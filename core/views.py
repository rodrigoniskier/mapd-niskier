import random
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import aluno_required, professor_required
from .forms import AjusteNotaForm, MensagemChatForm, PrimeiroAcessoForm, RGMAuthenticationForm
from .models import (
    AuditoriaNota, FonteConhecimento, MensagemChat, Questao, QuestaoTentativa,
    Resposta, SessaoChat, SlideRevisao, Tema, Tentativa, Turma, Usuario
)
from .services.gemini import (
    corrigir_discursiva, gerar_feedback, gerar_pacote_estudo, responder_tutor
)


class EntrarView(LoginView):
    template_name = "auth/login.html"
    authentication_form = RGMAuthenticationForm
    redirect_authenticated_user = True


class SairView(LogoutView):
    pass


def primeiro_acesso(request):
    if request.user.is_authenticated:
        return redirect("rotear_dashboard")
    form = PrimeiroAcessoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Cadastro realizado. Bem-vindo à plataforma MAPD Niskier.")
        return redirect("aluno_dashboard")
    return render(request, "auth/primeiro_acesso.html", {"form": form})


@login_required
def rotear_dashboard(request):
    if request.user.is_staff or request.user.papel == Usuario.Papel.PROFESSOR:
        return redirect("professor_dashboard")
    return redirect("aluno_dashboard")


@aluno_required
def aluno_dashboard(request):
    aulas = request.user.turma.aulas.select_related("tema").all() if request.user.turma else []
    temas = []
    vistos = set()
    for aula in aulas:
        if aula.tema and aula.disponivel_para_estudo and aula.tema.ativo and aula.tema.pk not in vistos:
            temas.append(aula.tema)
            vistos.add(aula.tema.pk)
    tentativas = request.user.tentativas.filter(status=Tentativa.Status.CONCLUIDA).select_related("tema")[:8]
    return render(request, "aluno/dashboard.html", {"aulas": aulas, "temas": temas, "tentativas": tentativas})


@aluno_required
def escolher_modo(request, slug):
    tema = get_object_or_404(Tema, slug=slug, ativo=True)
    return render(request, "aluno/escolher_modo.html", {"tema": tema})


@aluno_required
def revisar(request, slug):
    tema = get_object_or_404(Tema, slug=slug, ativo=True)
    slides = tema.slides.filter(aprovado=True)
    if not slides.exists():
        messages.info(request, "A revisão deste tema ainda está sendo preparada pelo professor.")
    return render(request, "aluno/revisar.html", {"tema": tema, "slides": slides})


def _montar_tentativa(aluno, tema):
    objetivas = list(tema.questoes.filter(tipo=Questao.Tipo.OBJETIVA, status=Questao.Status.APROVADA))
    discursivas = list(tema.questoes.filter(tipo=Questao.Tipo.DISCURSIVA, status=Questao.Status.APROVADA))
    if len(objetivas) < 9 or not discursivas:
        return None
    selecionadas = random.sample(objetivas, 9)
    discursiva = random.choice(discursivas)
    with transaction.atomic():
        tentativa = Tentativa.objects.create(aluno=aluno, tema=tema)
        for i, questao in enumerate(selecionadas, start=1):
            QuestaoTentativa.objects.create(
                tentativa=tentativa, questao=questao, ordem=i, valor=Decimal("0.80")
            )
        QuestaoTentativa.objects.create(
            tentativa=tentativa, questao=discursiva, ordem=10, valor=Decimal("2.80")
        )
    return tentativa


@aluno_required
def iniciar_avaliacao(request, slug):
    tema = get_object_or_404(Tema, slug=slug, ativo=True, pacote_publicado=True)
    em_andamento = request.user.tentativas.filter(
        tema=tema, status=Tentativa.Status.EM_ANDAMENTO
    ).first()
    tentativa = em_andamento or _montar_tentativa(request.user, tema)
    if not tentativa:
        messages.error(request, "Este tema ainda não possui um pacote completo de avaliação publicado.")
        return redirect("escolher_modo", slug=tema.slug)
    return redirect("avaliacao", pk=tentativa.pk)


@aluno_required
def avaliacao(request, pk):
    tentativa = get_object_or_404(Tentativa, pk=pk, aluno=request.user)
    if tentativa.status != Tentativa.Status.EM_ANDAMENTO:
        return redirect("resultado", pk=pk)
    itens = tentativa.itens.select_related("questao")
    sessao, _ = SessaoChat.objects.get_or_create(
        aluno=request.user, tema=tentativa.tema, tentativa=tentativa, contexto=SessaoChat.Contexto.QUESTAO
    )
    return render(request, "aluno/avaliacao.html", {
        "tentativa": tentativa, "itens": itens, "sessao": sessao, "chat_form": MensagemChatForm()
    })


@aluno_required
@transaction.atomic
def finalizar_avaliacao(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("Método inválido.")
    tentativa = get_object_or_404(Tentativa, pk=pk, aluno=request.user, status=Tentativa.Status.EM_ANDAMENTO)
    itens = tentativa.itens.select_related("questao")
    for item in itens:
        q = item.questao
        if q.tipo == Questao.Tipo.OBJETIVA:
            marcada = request.POST.get(f"q_{q.pk}", "").upper()
            correta = marcada == q.gabarito
            Resposta.objects.update_or_create(
                tentativa=tentativa, questao=q,
                defaults={
                    "alternativa_marcada": marcada,
                    "correta": correta,
                    "nota": item.valor if correta else Decimal("0.00"),
                    "comentario": q.justificativa,
                }
            )
        else:
            texto = request.POST.get(f"q_{q.pk}", "").strip()
            nota = Decimal("0.00")
            comentario = "Resposta registrada. Correção por IA indisponível; revisão docente necessária."
            status = Tentativa.Status.REVISAO
            if texto and settings.GEMINI_API_KEY:
                try:
                    correcao = corrigir_discursiva(q, texto)
                    nota = Decimal(str(correcao.nota)).quantize(Decimal("0.01"))
                    comentario = correcao.comentario
                    status = Tentativa.Status.CONCLUIDA
                except Exception:
                    status = Tentativa.Status.REVISAO
            Resposta.objects.update_or_create(
                tentativa=tentativa, questao=q,
                defaults={
                    "resposta_textual": texto,
                    "correta": None,
                    "nota": min(item.valor, nota),
                    "comentario": comentario,
                }
            )
            tentativa.status = status

    tentativa.concluida_em = timezone.now()
    if tentativa.status == Tentativa.Status.EM_ANDAMENTO:
        tentativa.status = Tentativa.Status.CONCLUIDA
    tentativa.save(update_fields=["concluida_em", "status"])
    tentativa.recalcular_nota()

    if settings.GEMINI_API_KEY:
        try:
            tentativa.feedback = gerar_feedback(tentativa)
            tentativa.save(update_fields=["feedback"])
        except Exception:
            messages.warning(request, "A nota foi registrada, mas o feedback detalhado será revisado depois.")
    return redirect("resultado", pk=tentativa.pk)


@aluno_required
def resultado(request, pk):
    tentativa = get_object_or_404(
        Tentativa.objects.select_related("tema", "aluno", "aluno__turma"), pk=pk, aluno=request.user
    )
    return render(request, "aluno/resultado.html", {"tentativa": tentativa})


@aluno_required
def feedback(request, pk):
    tentativa = get_object_or_404(Tentativa, pk=pk, aluno=request.user)
    itens = tentativa.itens.select_related("questao")
    respostas = {r.questao_id: r for r in tentativa.respostas.all()}
    linhas = [(item, respostas.get(item.questao_id)) for item in itens]
    return render(request, "aluno/feedback.html", {"tentativa": tentativa, "linhas": linhas})


@aluno_required
def plantao(request, slug):
    tema = get_object_or_404(Tema, slug=slug, ativo=True)
    sessao, _ = SessaoChat.objects.get_or_create(
        aluno=request.user, tema=tema, tentativa=None, contexto=SessaoChat.Contexto.PLANTAO
    )
    return render(request, "aluno/plantao.html", {
        "tema": tema, "sessao": sessao, "mensagens": sessao.mensagens.all(), "form": MensagemChatForm()
    })


@aluno_required
def chat_enviar(request, sessao_id):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido."}, status=405)
    sessao = get_object_or_404(SessaoChat, pk=sessao_id, aluno=request.user)
    form = MensagemChatForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"erro": "Mensagem inválida."}, status=400)
    texto = form.cleaned_data["mensagem"]
    MensagemChat.objects.create(sessao=sessao, autor=MensagemChat.Autor.ALUNO, texto=texto)
    historico = "\n".join(
        f"{m.get_autor_display()}: {m.texto}" for m in sessao.mensagens.order_by("-criada_em")[:8][::-1]
    )
    contexto_questao = ""
    if sessao.tentativa:
        contexto_questao = "\n".join(
            f"Q{i.ordem}: {i.questao.enunciado}" for i in sessao.tentativa.itens.select_related("questao")
        )
    try:
        resposta = responder_tutor(sessao.tema, texto, historico, contexto_questao)
        fontes = [f.model_dump() for f in resposta.fontes]
        msg = MensagemChat.objects.create(
            sessao=sessao, autor=MensagemChat.Autor.IA, texto=resposta.resposta, fontes=fontes
        )
        if sessao.tentativa:
            sessao.tentativa.quantidade_pistas += 1
            sessao.tentativa.save(update_fields=["quantidade_pistas"])
        return JsonResponse({"resposta": msg.texto, "fontes": fontes})
    except Exception as exc:
        return JsonResponse({
            "erro": "A IA Niskier está temporariamente indisponível. Sua pergunta ficou registrada."
        }, status=503)


@professor_required
def professor_dashboard(request):
    turma_id = request.GET.get("turma")
    tema_id = request.GET.get("tema")

    turmas = Turma.objects.prefetch_related("aulas", "alunos").annotate(
        media=Avg("alunos__tentativas__nota_total", filter=Q(alunos__tentativas__status=Tentativa.Status.CONCLUIDA)),
        concluidas=Count("alunos__tentativas", filter=Q(alunos__tentativas__status=Tentativa.Status.CONCLUIDA), distinct=True),
    )
    temas = Tema.objects.annotate(
        total_questoes=Count("questoes"),
        aprovadas=Count("questoes", filter=Q(questoes__status=Questao.Status.APROVADA)),
        media=Avg("tentativas__nota_total", filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA)),
        concluidas=Count("tentativas", filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA), distinct=True),
    )

    tentativas_qs = Tentativa.objects.select_related("aluno", "aluno__turma", "tema")
    alunos_qs = Usuario.objects.filter(papel=Usuario.Papel.ALUNO).select_related("turma")
    if turma_id:
        tentativas_qs = tentativas_qs.filter(aluno__turma_id=turma_id)
        alunos_qs = alunos_qs.filter(turma_id=turma_id)
    if tema_id:
        tentativas_qs = tentativas_qs.filter(tema_id=tema_id)

    alunos_desempenho = alunos_qs.annotate(
        media=Avg(
            "tentativas__nota_total",
            filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA)
            & (Q(tentativas__tema_id=tema_id) if tema_id else Q()),
        ),
        concluidas=Count(
            "tentativas",
            filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA)
            & (Q(tentativas__tema_id=tema_id) if tema_id else Q()),
            distinct=True,
        ),
    ).order_by("turma__codigo", "first_name")

    tentativas = tentativas_qs[:100]
    metricas_base = Tentativa.objects.filter(status=Tentativa.Status.CONCLUIDA)
    if turma_id:
        metricas_base = metricas_base.filter(aluno__turma_id=turma_id)
    if tema_id:
        metricas_base = metricas_base.filter(tema_id=tema_id)
    metricas = {
        "alunos": alunos_qs.count(),
        "concluidas": metricas_base.count(),
        "media": metricas_base.aggregate(m=Avg("nota_total"))["m"],
        "revisao": Tentativa.objects.filter(status=Tentativa.Status.REVISAO).count(),
    }
    return render(request, "professor/dashboard.html", {
        "turmas": turmas, "temas": temas, "tentativas": tentativas, "metricas": metricas,
        "alunos_desempenho": alunos_desempenho, "turma_id": turma_id or "", "tema_id": tema_id or "",
    })


@professor_required
@transaction.atomic
def gerar_pacote(request, tema_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Método inválido.")
    tema = get_object_or_404(Tema, pk=tema_id)
    try:
        pacote = gerar_pacote_estudo(tema)
    except Exception as exc:
        messages.error(request, f"Não foi possível gerar o pacote: {exc}")
        return redirect("professor_dashboard")

    tema.slides.all().delete()
    tema.questoes.filter(criada_por_ia=True, status=Questao.Status.RASCUNHO).delete()
    for slide in pacote.slides[:3]:
        SlideRevisao.objects.create(
            tema=tema, ordem=slide.ordem, titulo=slide.titulo, conteudo=slide.conteudo, aprovado=False
        )
    for q in pacote.objetivas[:9]:
        Questao.objects.create(
            tema=tema, tipo=Questao.Tipo.OBJETIVA, enunciado=q.enunciado,
            alternativas=q.alternativas, gabarito=q.gabarito, justificativa=q.justificativa,
            dificuldade=q.dificuldade, nivel_cognitivo=q.nivel_cognitivo,
            status=Questao.Status.RASCUNHO, criada_por_ia=True
        )
    Questao.objects.create(
        tema=tema, tipo=Questao.Tipo.DISCURSIVA, enunciado=pacote.discursiva.enunciado,
        erros_propositais=pacote.discursiva.erros_propositais,
        justificativa=pacote.discursiva.justificativa,
        status=Questao.Status.RASCUNHO, criada_por_ia=True
    )
    tema.pacote_publicado = False
    tema.save(update_fields=["pacote_publicado"])
    messages.success(request, "Pacote gerado como rascunho. Revise no Admin antes de publicar.")
    return redirect("professor_dashboard")


@professor_required
@transaction.atomic
def publicar_pacote(request, tema_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Método inválido.")
    tema = get_object_or_404(Tema, pk=tema_id)
    if tema.slides.count() < 2 or tema.questoes.filter(tipo=Questao.Tipo.OBJETIVA).count() < 9 or not tema.questoes.filter(tipo=Questao.Tipo.DISCURSIVA).exists():
        messages.error(request, "O pacote precisa ter pelo menos 2 slides, 9 objetivas e 1 discursiva.")
        return redirect("professor_dashboard")
    tema.slides.update(aprovado=True)
    tema.questoes.exclude(status=Questao.Status.ARQUIVADA).update(status=Questao.Status.APROVADA)
    tema.pacote_publicado = True
    tema.save(update_fields=["pacote_publicado"])
    messages.success(request, f"Pacote “{tema.titulo}” publicado.")
    return redirect("professor_dashboard")


@professor_required
def ajustar_nota(request, tentativa_id):
    tentativa = get_object_or_404(Tentativa, pk=tentativa_id)
    form = AjusteNotaForm(request.POST or None, initial={"nota": tentativa.nota_total})
    if request.method == "POST" and form.is_valid():
        anterior = tentativa.nota_total
        tentativa.nota_total = form.cleaned_data["nota"]
        tentativa.status = Tentativa.Status.CONCLUIDA
        tentativa.save(update_fields=["nota_total", "status"])
        AuditoriaNota.objects.create(
            tentativa=tentativa, alterada_por=request.user,
            nota_anterior=anterior, nota_nova=tentativa.nota_total,
            justificativa=form.cleaned_data["justificativa"]
        )
        messages.success(request, "Nota ajustada e registrada na auditoria.")
        return redirect("professor_dashboard")
    return render(request, "professor/ajustar_nota.html", {"tentativa": tentativa, "form": form})
