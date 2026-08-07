from .common import *
from .learning import _tema_aluno


@aluno_required
def plantao(request, slug):
    tema = _tema_aluno(request, slug)
    sessao, _ = SessaoChat.objects.get_or_create(
        aluno=request.user,
        tema=tema,
        tentativa=None,
        contexto=SessaoChat.Contexto.PLANTAO,
        defaults={"ativa": True},
    )
    return render(
        request,
        "aluno/plantao.html",
        {
            "tema": tema,
            "sessao": sessao,
            "mensagens": sessao.mensagens.all(),
            "form": MensagemChatForm(),
        },
    )


@aluno_required
@require_POST
def chat_enviar(request, sessao_id):
    sessao = get_object_or_404(SessaoChat, pk=sessao_id, aluno=request.user, ativa=True)
    form = MensagemChatForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"erro": "Mensagem inválida.", "detalhes": form.errors.get_json_data()},
            status=400,
        )
    texto = form.cleaned_data["mensagem"]
    questao = None
    contexto_questao = ""
    if sessao.tentativa and form.cleaned_data.get("questao_id"):
        questao = get_object_or_404(
            Questao,
            pk=form.cleaned_data["questao_id"],
            questaotentativa__tentativa=sessao.tentativa,
        )
        alternativas = "\n".join(f"{k}) {v}" for k, v in (questao.alternativas or {}).items())
        contexto_questao = f"ENUNCIADO:\n{questao.enunciado}\nALTERNATIVAS:\n{alternativas}"
    nivel_pista = form.cleaned_data.get("nivel_pista") or 1
    MensagemChat.objects.create(
        sessao=sessao,
        autor=MensagemChat.Autor.ALUNO,
        texto=texto,
        questao=questao,
        nivel_pista=nivel_pista if sessao.tentativa else 0,
    )
    historico = "\n".join(
        f"{m.get_autor_display()}: {m.texto}"
        for m in list(sessao.mensagens.order_by("-criada_em")[:16])[::-1]
    )
    try:
        resposta = responder_tutor(
            sessao.tema,
            texto,
            historico,
            contexto_questao,
            nivel_pista=nivel_pista,
            modo_questao=bool(sessao.tentativa),
        )
        fontes = [f.model_dump() for f in resposta.fontes]
        msg = MensagemChat.objects.create(
            sessao=sessao,
            autor=MensagemChat.Autor.IA,
            texto=resposta.resposta,
            fontes=fontes,
            questao=questao,
            nivel_pista=resposta.nivel_pista,
        )
        if sessao.tentativa:
            sessao.tentativa.quantidade_pistas += 1
            sessao.tentativa.save(update_fields=["quantidade_pistas"])
            if questao:
                item = sessao.tentativa.itens.filter(questao=questao).first()
                if item:
                    item.ajuda_usada += 1
                    item.save(update_fields=["ajuda_usada"])
        return JsonResponse({"resposta": msg.texto, "fontes": fontes, "nivel_pista": resposta.nivel_pista})
    except Exception:
        return JsonResponse(
            {"erro": "A IA Niskier está temporariamente indisponível. Sua pergunta ficou registrada."},
            status=503,
        )


@never_cache
def service_worker(request):
    caminho = settings.BASE_DIR / "static" / "sw.js"
    resposta = HttpResponse(caminho.read_text(encoding="utf-8"), content_type="application/javascript")
    resposta["Service-Worker-Allowed"] = "/"
    return resposta
