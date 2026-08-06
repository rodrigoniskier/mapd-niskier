from .common import *


def _tema_aluno(request, slug, exigir_publicado=False):
    tema = get_object_or_404(Tema, slug=slug, ativo=True)
    if not request.user.turma or not tema.pertence_a_turma(request.user.turma):
        raise Http404("Tema não disponível para esta turma.")
    if not tema.liberado_agora:
        raise Http404("Tema ainda não liberado.")
    if exigir_publicado and not tema.pacote_publicado:
        raise Http404("Pacote de avaliação ainda não publicado.")
    return tema


@aluno_required
def aluno_dashboard(request):
    turma = request.user.turma
    aulas = turma.aulas.select_related("tema").all() if turma else Aula.objects.none()
    temas = []
    vistos = set()
    for aula in aulas:
        tema = aula.tema
        if not tema or tema.pk in vistos or not aula.disponivel_para_estudo:
            continue
        vistos.add(tema.pk)
        revisao = RevisaoProgresso.objects.filter(aluno=request.user, tema=tema).first()
        ultima = request.user.tentativas.filter(tema=tema).first()
        temas.append(
            {
                "tema": tema,
                "aula": aula,
                "liberado": tema.liberado_agora,
                "revisao_concluida": bool(revisao and revisao.concluida),
                "ultima_tentativa": ultima,
                "tentativas": request.user.tentativas.filter(tema=tema).count(),
            }
        )
    concluidas = request.user.tentativas.filter(status=Tentativa.Status.CONCLUIDA)
    metricas = {
        "concluidas": concluidas.count(),
        "media": concluidas.aggregate(m=Avg("nota_total"))["m"],
        "pistas": concluidas.aggregate(n=Count("sessoes_chat__mensagens"))["n"] or 0,
    }
    return render(
        request,
        "aluno/dashboard.html",
        {
            "turma": turma,
            "temas": temas,
            "aulas": aulas[:8],
            "tentativas": request.user.tentativas.select_related("tema")[:8],
            "metricas": metricas,
        },
    )


@aluno_required
def escolher_modo(request, slug):
    tema = _tema_aluno(request, slug)
    revisao = RevisaoProgresso.objects.filter(aluno=request.user, tema=tema).first()
    tentativas = request.user.tentativas.filter(tema=tema)
    return render(
        request,
        "aluno/escolher_modo.html",
        {
            "tema": tema,
            "revisao": revisao,
            "tentativas": tentativas,
            "pode_tentar": tentativas.count() < tema.tentativas_permitidas,
        },
    )


@aluno_required
def revisar(request, slug):
    tema = _tema_aluno(request, slug)
    slides = tema.slides.filter(aprovado=True).order_by("ordem")[:3]
    progresso, _ = RevisaoProgresso.objects.get_or_create(aluno=request.user, tema=tema)
    if not slides.exists():
        messages.info(request, "A revisão deste tema ainda está sendo preparada pelo professor.")
    return render(
        request,
        "aluno/revisar.html",
        {"tema": tema, "slides": slides, "progresso": progresso},
    )


@aluno_required
@require_POST
def concluir_revisao(request, slug):
    tema = _tema_aluno(request, slug)
    progresso, _ = RevisaoProgresso.objects.get_or_create(aluno=request.user, tema=tema)
    progresso.slide_atual = min(3, tema.slides.filter(aprovado=True).count() or 1)
    progresso.concluida_em = timezone.now()
    progresso.save(update_fields=["slide_atual", "concluida_em", "atualizada_em"])
    messages.success(request, "Revisão concluída. Prepare-se para 9 questões objetivas e 1 discursiva.")
    return redirect("pre_avaliacao", slug=tema.slug)


@aluno_required
def pre_avaliacao(request, slug):
    tema = _tema_aluno(request, slug, exigir_publicado=True)
    progresso = RevisaoProgresso.objects.filter(aluno=request.user, tema=tema).first()
    if not progresso or not progresso.concluida:
        messages.warning(request, "Conclua a revisão rápida antes de iniciar o teste.")
        return redirect("revisar", slug=tema.slug)
    return render(request, "aluno/pre_avaliacao.html", {"tema": tema})


def _montar_tentativa(aluno, tema):
    objetivas, discursiva, nivel = selecionar_questoes(aluno, tema)
    if len(objetivas) < 9 or not discursiva:
        return None
    versao = aluno.tentativas.filter(tema=tema).count() + 1
    with transaction.atomic():
        tentativa = Tentativa.objects.create(
            aluno=aluno,
            tema=tema,
            nivel_adaptativo=nivel,
            versao=versao,
        )
        for i, questao in enumerate(objetivas, start=1):
            QuestaoTentativa.objects.create(
                tentativa=tentativa,
                questao=questao,
                ordem=i,
                valor=Decimal("0.80"),
            )
        QuestaoTentativa.objects.create(
            tentativa=tentativa,
            questao=discursiva,
            ordem=10,
            valor=Decimal("2.80"),
        )
    return tentativa


@aluno_required
@require_POST
def iniciar_avaliacao(request, slug):
    tema = _tema_aluno(request, slug, exigir_publicado=True)
    progresso = RevisaoProgresso.objects.filter(aluno=request.user, tema=tema).first()
    if not progresso or not progresso.concluida:
        messages.warning(request, "Conclua a revisão antes de iniciar a avaliação.")
        return redirect("revisar", slug=tema.slug)
    em_andamento = request.user.tentativas.filter(
        tema=tema, status=Tentativa.Status.EM_ANDAMENTO
    ).first()
    if em_andamento:
        return redirect("avaliacao", pk=em_andamento.pk)
    if request.user.tentativas.filter(tema=tema).count() >= tema.tentativas_permitidas:
        messages.error(request, "Você atingiu o limite de tentativas deste tema.")
        return redirect("escolher_modo", slug=tema.slug)
    tentativa = _montar_tentativa(request.user, tema)
    if not tentativa:
        messages.error(request, "O tema ainda não possui 9 objetivas e 1 discursiva aprovadas.")
        return redirect("escolher_modo", slug=tema.slug)
    return redirect("avaliacao", pk=tentativa.pk)
