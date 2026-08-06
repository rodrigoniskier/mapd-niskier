from .common import *


def _tentativas_filtradas(request):
    qs = Tentativa.objects.select_related("aluno", "aluno__turma", "tema")
    turma_id = request.GET.get("turma", "")
    tema_id = request.GET.get("tema", "")
    aluno = request.GET.get("aluno", "").strip()
    status = request.GET.get("status", "")
    if turma_id:
        qs = qs.filter(aluno__turma_id=turma_id)
    if tema_id:
        qs = qs.filter(tema_id=tema_id)
    if aluno:
        qs = qs.filter(Q(aluno__first_name__icontains=aluno) | Q(aluno__last_name__icontains=aluno) | Q(aluno__rgm__icontains=aluno))
    if status:
        qs = qs.filter(status=status)
    return qs, {"turma": turma_id, "tema": tema_id, "aluno": aluno, "status": status}


@professor_required
def professor_dashboard(request):
    tentativas_qs, filtros = _tentativas_filtradas(request)
    concluidas = tentativas_qs.filter(status=Tentativa.Status.CONCLUIDA)
    metricas = {
        "alunos": Usuario.objects.filter(papel=Usuario.Papel.ALUNO, is_active=True).count(),
        "concluidas": concluidas.count(),
        "media": concluidas.aggregate(m=Avg("nota_total"))["m"],
        "revisao": tentativas_qs.filter(status=Tentativa.Status.REVISAO).count(),
        "temas_publicados": Tema.objects.filter(pacote_publicado=True).count(),
    }
    por_tema = list(
        concluidas.values("tema__titulo").annotate(media=Avg("nota_total"), total=Count("id")).order_by("tema__ordem")
    )
    por_turma = list(
        concluidas.values("aluno__turma__codigo").annotate(media=Avg("nota_total"), total=Count("id")).order_by("aluno__turma__codigo")
    )
    temas = Tema.objects.annotate(
        total_questoes=Count("questoes", distinct=True),
        aprovadas=Count("questoes", filter=Q(questoes__status=Questao.Status.APROVADA), distinct=True),
        media=Avg("tentativas__nota_total", filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA)),
        concluidas=Count("tentativas", filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA), distinct=True),
    )
    alunos = Usuario.objects.filter(papel=Usuario.Papel.ALUNO).select_related("turma").annotate(
        media=Avg("tentativas__nota_total", filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA)),
        concluidas=Count("tentativas", filter=Q(tentativas__status=Tentativa.Status.CONCLUIDA)),
    )
    return render(
        request,
        "professor/dashboard.html",
        {
            "metricas": metricas,
            "temas": temas,
            "turmas": Turma.objects.all(),
            "alunos": alunos[:100],
            "tentativas": tentativas_qs[:100],
            "filtros": filtros,
            "chart_temas": json.dumps(por_tema, default=str),
            "chart_turmas": json.dumps(por_turma, default=str),
            "tarefas_ia": TarefaIA.objects.select_related("tema", "tentativa")[:8],
        },
    )


@professor_required
def professor_tema(request, tema_id):
    tema = get_object_or_404(Tema, pk=tema_id)
    return render(
        request,
        "professor/tema_detail.html",
        {
            "tema": tema,
            "slides": tema.slides.all(),
            "objetivas": tema.questoes.filter(tipo=Questao.Tipo.OBJETIVA),
            "discursivas": tema.questoes.filter(tipo=Questao.Tipo.DISCURSIVA),
            "aulas": tema.aulas.select_related("turma"),
        },
    )
