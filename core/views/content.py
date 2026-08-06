from .common import *


@professor_required
def tema_editar(request, tema_id=None):
    tema = get_object_or_404(Tema, pk=tema_id) if tema_id else Tema()
    form = TemaForm(request.POST or None, instance=tema)
    if request.method == "POST" and form.is_valid():
        tema = form.save()
        messages.success(request, "Tema salvo.")
        return redirect("professor_tema", tema_id=tema.pk)
    return render(request, "professor/form.html", {"form": form, "titulo": "Editar tema" if tema_id else "Novo tema"})


@professor_required
def aula_editar(request, aula_id=None):
    aula = get_object_or_404(Aula, pk=aula_id) if aula_id else Aula()
    form = AulaForm(request.POST or None, instance=aula)
    if request.method == "POST" and form.is_valid():
        aula = form.save()
        messages.success(request, "Entrada de cronograma salva.")
        return redirect("professor_dashboard")
    return render(request, "professor/form.html", {"form": form, "titulo": "Editar cronograma" if aula_id else "Nova entrada de cronograma"})


@professor_required
def slide_editar(request, tema_id, slide_id=None):
    tema = get_object_or_404(Tema, pk=tema_id)
    slide = get_object_or_404(SlideRevisao, pk=slide_id, tema=tema) if slide_id else SlideRevisao(tema=tema)
    form = SlideRevisaoForm(request.POST or None, instance=slide)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.tema = tema
        obj.save()
        messages.success(request, "Tela de revisão salva.")
        return redirect("professor_tema", tema_id=tema.pk)
    return render(request, "professor/form.html", {"form": form, "titulo": "Tela de revisão", "tema": tema})


@professor_required
def questao_editar(request, tema_id, questao_id=None):
    tema = get_object_or_404(Tema, pk=tema_id)
    questao = get_object_or_404(Questao, pk=questao_id, tema=tema) if questao_id else Questao(tema=tema)
    form = QuestaoForm(request.POST or None, instance=questao)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.tema = tema
        if obj.status == Questao.Status.APROVADA:
            obj.revisada_por = request.user
            obj.revisada_em = timezone.now()
        obj.save()
        messages.success(request, "Questão salva.")
        return redirect("professor_tema", tema_id=tema.pk)
    return render(request, "professor/form.html", {"form": form, "titulo": "Questão", "tema": tema})


@professor_required
@require_POST
def questao_status(request, questao_id):
    questao = get_object_or_404(Questao, pk=questao_id)
    novo = request.POST.get("status")
    if novo not in Questao.Status.values:
        return HttpResponseBadRequest("Status inválido.")
    questao.status = novo
    if novo == Questao.Status.APROVADA:
        questao.revisada_por = request.user
        questao.revisada_em = timezone.now()
    questao.save(update_fields=["status", "revisada_por", "revisada_em", "atualizada_em"])
    messages.success(request, "Status da questão atualizado.")
    return redirect("professor_tema", tema_id=questao.tema_id)


@professor_required
@transaction.atomic
@require_POST
def gerar_pacote(request, tema_id):
    tema = get_object_or_404(Tema, pk=tema_id)
    tarefa = TarefaIA.objects.create(tipo=TarefaIA.Tipo.PACOTE, tema=tema, solicitada_por=request.user)
    tarefa.status = TarefaIA.Status.PROCESSANDO
    tarefa.iniciada_em = timezone.now()
    tarefa.save(update_fields=["status", "iniciada_em"])
    try:
        pacote = gerar_pacote_estudo(tema)
        tema.slides.filter(aprovado=False).delete()
        tema.questoes.filter(criada_por_ia=True, status=Questao.Status.RASCUNHO).delete()
        for slide in pacote.slides[:3]:
            SlideRevisao.objects.update_or_create(
                tema=tema,
                ordem=slide.ordem,
                defaults={
                    "titulo": slide.titulo,
                    "conteudo": slide.conteudo,
                    "pontos_chave": slide.pontos_chave,
                    "aprovado": False,
                },
            )
        for q in pacote.objetivas[:15]:
            Questao.objects.create(
                tema=tema,
                tipo=Questao.Tipo.OBJETIVA,
                enunciado=q.enunciado,
                alternativas=q.alternativas,
                gabarito=q.gabarito,
                justificativa=q.justificativa,
                dificuldade=q.dificuldade,
                nivel_cognitivo=q.nivel_cognitivo,
                habilidade=q.habilidade,
                referencias=[f.model_dump() for f in q.referencias],
                status=Questao.Status.RASCUNHO,
                criada_por_ia=True,
            )
        for q in pacote.discursivas[:2]:
            Questao.objects.create(
                tema=tema,
                tipo=Questao.Tipo.DISCURSIVA,
                enunciado=q.enunciado,
                erros_propositais=q.erros_propositais,
                justificativa=q.justificativa,
                habilidade=q.habilidade,
                referencias=[f.model_dump() for f in q.referencias],
                status=Questao.Status.RASCUNHO,
                criada_por_ia=True,
            )
        tema.pacote_publicado = False
        tema.save(update_fields=["pacote_publicado"])
        tarefa.status = TarefaIA.Status.CONCLUIDA
        tarefa.concluida_em = timezone.now()
        tarefa.save(update_fields=["status", "concluida_em"])
        messages.success(request, "Pacote completo gerado como rascunho: 3 telas, 15 objetivas e 2 discursivas.")
    except Exception as exc:
        tarefa.status = TarefaIA.Status.ERRO
        tarefa.mensagem_erro = str(exc)[:4000]
        tarefa.concluida_em = timezone.now()
        tarefa.save(update_fields=["status", "mensagem_erro", "concluida_em"])
        messages.error(request, f"Não foi possível gerar o pacote: {exc}")
    return redirect("professor_tema", tema_id=tema.pk)


@professor_required
@transaction.atomic
@require_POST
def aprovar_rascunhos(request, tema_id):
    tema = get_object_or_404(Tema, pk=tema_id)
    tema.slides.update(aprovado=True)
    tema.questoes.filter(status=Questao.Status.RASCUNHO).update(
        status=Questao.Status.APROVADA,
        revisada_por=request.user,
        revisada_em=timezone.now(),
    )
    messages.success(request, "Rascunhos aprovados. Faça uma revisão amostral antes de publicar.")
    return redirect("professor_tema", tema_id=tema.pk)


@professor_required
@require_POST
def publicar_pacote(request, tema_id):
    tema = get_object_or_404(Tema, pk=tema_id)
    slides = tema.slides.filter(aprovado=True).count()
    objetivas = tema.questoes.filter(tipo=Questao.Tipo.OBJETIVA, status=Questao.Status.APROVADA).count()
    discursivas = tema.questoes.filter(tipo=Questao.Tipo.DISCURSIVA, status=Questao.Status.APROVADA).count()
    if slides < 2 or objetivas < 9 or discursivas < 1:
        messages.error(request, "Para publicar, aprove ao menos 2 telas, 9 objetivas e 1 discursiva.")
    else:
        tema.pacote_publicado = True
        tema.save(update_fields=["pacote_publicado"])
        messages.success(request, f"Pacote “{tema.titulo}” publicado para os alunos.")
    return redirect("professor_tema", tema_id=tema.pk)


@professor_required
@require_POST
def despublicar_pacote(request, tema_id):
    tema = get_object_or_404(Tema, pk=tema_id)
    tema.pacote_publicado = False
    tema.save(update_fields=["pacote_publicado"])
    messages.success(request, "Pacote retirado da área de avaliação.")
    return redirect("professor_tema", tema_id=tema.pk)
