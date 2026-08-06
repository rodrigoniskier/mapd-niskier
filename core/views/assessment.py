from .common import *
from .learning import _montar_tentativa, _tema_aluno


@aluno_required
def avaliacao(request, pk):
    tentativa = get_object_or_404(Tentativa, pk=pk, aluno=request.user)
    if tentativa.status != Tentativa.Status.EM_ANDAMENTO:
        return redirect("resultado", pk=pk)
    respostas = {r.questao_id: r for r in tentativa.respostas.all()}
    itens = [
        {"item": item, "resposta": respostas.get(item.questao_id)}
        for item in tentativa.itens.select_related("questao")
    ]
    sessao, _ = SessaoChat.objects.get_or_create(
        aluno=request.user,
        tema=tentativa.tema,
        tentativa=tentativa,
        contexto=SessaoChat.Contexto.QUESTAO,
        defaults={"ativa": True},
    )
    return render(
        request,
        "aluno/avaliacao.html",
        {
            "tentativa": tentativa,
            "itens": itens,
            "sessao": sessao,
            "chat_form": MensagemChatForm(),
            "aviso": ConfiguracaoPlataforma.atual().aviso_avaliacao,
        },
    )


@aluno_required
@require_POST
def salvar_resposta(request, pk):
    tentativa = get_object_or_404(
        Tentativa, pk=pk, aluno=request.user, status=Tentativa.Status.EM_ANDAMENTO
    )
    questao_id = request.POST.get("questao_id")
    questao = get_object_or_404(Questao, pk=questao_id, questaotentativa__tentativa=tentativa)
    defaults = {}
    if questao.tipo == Questao.Tipo.OBJETIVA:
        defaults["alternativa_marcada"] = request.POST.get("alternativa", "").upper()[:1]
    else:
        defaults["resposta_textual"] = request.POST.get("texto", "")[:12000]
    resposta, _ = Resposta.objects.update_or_create(
        tentativa=tentativa, questao=questao, defaults=defaults
    )
    return JsonResponse({"ok": True, "salva_em": resposta.salva_em.isoformat()})


@aluno_required
@transaction.atomic
@require_POST
def finalizar_avaliacao(request, pk):
    tentativa = get_object_or_404(
        Tentativa, pk=pk, aluno=request.user, status=Tentativa.Status.EM_ANDAMENTO
    )
    itens = list(tentativa.itens.select_related("questao"))
    for item in itens:
        q = item.questao
        if q.tipo == Questao.Tipo.OBJETIVA:
            marcada = request.POST.get(f"q_{q.pk}", "").upper()[:1]
            correta = bool(marcada and marcada == q.gabarito)
            Resposta.objects.update_or_create(
                tentativa=tentativa,
                questao=q,
                defaults={
                    "alternativa_marcada": marcada,
                    "correta": correta,
                    "nota": item.valor if correta else Decimal("0.00"),
                    "comentario": q.justificativa,
                },
            )
        else:
            texto = request.POST.get(f"q_{q.pk}", "").strip()[:12000]
            nota = Decimal("0.00")
            comentario = "Resposta registrada; correção docente recomendada."
            precisa_revisao = True
            if texto and settings.GEMINI_API_KEY:
                try:
                    correcao = corrigir_discursiva(q, texto)
                    nota = Decimal(str(correcao.nota)).quantize(Decimal("0.01"))
                    comentario = correcao.comentario
                    precisa_revisao = correcao.precisa_revisao_docente
                except Exception:
                    pass
            Resposta.objects.update_or_create(
                tentativa=tentativa,
                questao=q,
                defaults={
                    "resposta_textual": texto,
                    "correta": None,
                    "nota": min(item.valor, nota),
                    "comentario": comentario,
                },
            )
            if precisa_revisao:
                tentativa.status = Tentativa.Status.REVISAO

    tentativa.concluida_em = timezone.now()
    duracao = int((tentativa.concluida_em - tentativa.iniciada_em).total_seconds())
    tentativa.duracao_segundos = max(0, duracao)
    if tentativa.status == Tentativa.Status.EM_ANDAMENTO:
        tentativa.status = Tentativa.Status.CONCLUIDA
    tentativa.save(update_fields=["concluida_em", "duracao_segundos", "status"])
    tentativa.recalcular_nota()

    tentativa.feedback = feedback_deterministico(tentativa)
    if settings.GEMINI_API_KEY:
        try:
            tentativa.feedback = gerar_feedback(tentativa)
            tentativa.feedback_gerado_em = timezone.now()
        except Exception:
            messages.warning(
                request,
                "A avaliação foi concluída. O feedback básico está disponível; o detalhamento por IA poderá ser reprocessado.",
            )
    tentativa.save(update_fields=["feedback", "feedback_gerado_em"])
    RegistroAuditoria.objects.create(
        usuario=request.user,
        acao="AVALIACAO_CONCLUIDA",
        objeto="Tentativa",
        objeto_id=str(tentativa.pk),
        detalhes={"tema": tentativa.tema_id, "nota": str(tentativa.nota_total)},
    )
    return redirect("resultado", pk=tentativa.pk)


@aluno_required
def resultado(request, pk):
    tentativa = get_object_or_404(
        Tentativa.objects.select_related("tema", "aluno", "aluno__turma"),
        pk=pk,
        aluno=request.user,
    )
    validation_url = request.build_absolute_uri(
        reverse("validar_comprovante", args=[tentativa.codigo_comprovante])
    )
    return render(
        request,
        "aluno/resultado.html",
        {
            "tentativa": tentativa,
            "validation_url": validation_url,
            "qr_data_uri": qr_data_uri(validation_url),
        },
    )


@aluno_required
def feedback(request, pk):
    tentativa = get_object_or_404(Tentativa, pk=pk, aluno=request.user)
    respostas = {r.questao_id: r for r in tentativa.respostas.all()}
    linhas = [
        (item, respostas.get(item.questao_id))
        for item in tentativa.itens.select_related("questao")
    ]
    return render(
        request,
        "aluno/feedback.html",
        {"tentativa": tentativa, "linhas": linhas},
    )


@aluno_required
def certificado_pdf(request, pk):
    tentativa = get_object_or_404(Tentativa, pk=pk, aluno=request.user)
    validation_url = request.build_absolute_uri(
        reverse("validar_comprovante", args=[tentativa.codigo_comprovante])
    )
    return certificado_pdf_response(tentativa, validation_url)


def validar_comprovante(request, codigo):
    tentativa = get_object_or_404(
        Tentativa.objects.select_related("aluno", "aluno__turma", "tema"),
        codigo_comprovante=codigo,
    )
    return render(request, "aluno/validar.html", {"tentativa": tentativa})
