from .common import *
from .dashboard import _tentativas_filtradas


@professor_required
def tentativa_detalhe(request, tentativa_id):
    tentativa = get_object_or_404(
        Tentativa.objects.select_related("aluno", "aluno__turma", "tema"), pk=tentativa_id
    )
    respostas = {r.questao_id: r for r in tentativa.respostas.all()}
    linhas = [(i, respostas.get(i.questao_id)) for i in tentativa.itens.select_related("questao")]
    return render(
        request,
        "professor/tentativa_detail.html",
        {"tentativa": tentativa, "linhas": linhas, "auditorias": tentativa.auditorias.all()},
    )


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
            tentativa=tentativa,
            alterada_por=request.user,
            nota_anterior=anterior,
            nota_nova=tentativa.nota_total,
            justificativa=form.cleaned_data["justificativa"],
        )
        messages.success(request, "Nota ajustada e registrada na auditoria.")
        return redirect("tentativa_detalhe", tentativa_id=tentativa.pk)
    return render(request, "professor/ajustar_nota.html", {"tentativa": tentativa, "form": form})


@professor_required
@require_POST
def reprocessar_feedback(request, tentativa_id):
    tentativa = get_object_or_404(Tentativa, pk=tentativa_id)
    try:
        tentativa.feedback = gerar_feedback(tentativa) if settings.GEMINI_API_KEY else feedback_deterministico(tentativa)
        tentativa.feedback_gerado_em = timezone.now()
        tentativa.save(update_fields=["feedback", "feedback_gerado_em"])
        messages.success(request, "Feedback reprocessado.")
    except Exception as exc:
        messages.error(request, f"Falha ao reprocessar: {exc}")
    return redirect("tentativa_detalhe", tentativa_id=tentativa.pk)


@professor_required
def aluno_editar(request, aluno_id):
    aluno = get_object_or_404(Usuario, pk=aluno_id, papel=Usuario.Papel.ALUNO)
    form = AlunoForm(request.POST or None, instance=aluno)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Cadastro do aluno atualizado.")
        return redirect("professor_dashboard")
    return render(request, "professor/form.html", {"form": form, "titulo": "Editar aluno"})


@professor_required
def professor_fontes(request):
    return render(
        request,
        "professor/fontes.html",
        {"fontes": FonteConhecimento.objects.all()},
    )


@professor_required
def fonte_editar(request, fonte_id=None):
    fonte = get_object_or_404(FonteConhecimento, pk=fonte_id) if fonte_id else FonteConhecimento()
    form = FonteConhecimentoForm(request.POST or None, instance=fonte)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.auditada_em = timezone.now()
        obj.save()
        messages.success(request, "Fonte salva e registrada para auditoria.")
        return redirect("professor_fontes")
    return render(request, "professor/form.html", {"form": form, "titulo": "Fonte de conhecimento"})


@professor_required
@require_POST
def fonte_importar(request, fonte_id):
    fonte = get_object_or_404(FonteConhecimento, pk=fonte_id)
    if not fonte.url:
        messages.error(request, "A fonte não possui URL.")
        return redirect("professor_fontes")
    try:
        import requests
        from bs4 import BeautifulSoup

        response = requests.get(
            fonte.url,
            timeout=20,
            headers={"User-Agent": "MAPD-Niskier/1.0 academic-source-audit"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "form"]):
            tag.decompose()
        fonte.conteudo = "\n".join(x.strip() for x in soup.get_text("\n").splitlines() if x.strip())[:120000]
        fonte.auditada_em = timezone.now()
        fonte.save(update_fields=["conteudo", "auditada_em", "atualizada_em"])
        messages.success(request, "Conteúdo público importado. Revise antes de manter a fonte aprovada.")
    except Exception as exc:
        messages.error(request, f"Falha na importação: {exc}")
    return redirect("professor_fontes")


@professor_required
def relatorios(request):
    tentativas, filtros = _tentativas_filtradas(request)
    concluidas = tentativas.filter(status__in=[Tentativa.Status.CONCLUIDA, Tentativa.Status.REVISAO])
    return render(
        request,
        "professor/relatorios.html",
        {
            "tentativas": concluidas[:300],
            "filtros": filtros,
            "turmas": Turma.objects.all(),
            "temas": Tema.objects.all(),
            "media": concluidas.aggregate(m=Avg("nota_total"))["m"],
        },
    )


@professor_required
def relatorio_csv(request):
    tentativas, _ = _tentativas_filtradas(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="desempenho-mapd.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Aluno", "RGM", "Turma", "Tema", "Nota objetiva", "Nota discursiva", "Nota total", "Pistas", "Status", "Data"])
    for t in tentativas:
        writer.writerow(
            [
                t.aluno.nome_exibicao,
                t.aluno.rgm or t.aluno.username,
                t.aluno.turma.codigo if t.aluno.turma else "",
                t.tema.titulo,
                t.nota_objetiva,
                t.nota_discursiva,
                t.nota_total,
                t.quantidade_pistas,
                t.get_status_display(),
                t.concluida_em.strftime("%d/%m/%Y %H:%M") if t.concluida_em else "",
            ]
        )
    return response


@professor_required
def relatorio_pdf(request):
    tentativas, _ = _tentativas_filtradas(request)
    return relatorio_pdf_response(tentativas[:1000])
