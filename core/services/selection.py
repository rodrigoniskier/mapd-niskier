import random
from collections import defaultdict
from decimal import Decimal

from django.db.models import Avg

from core.models import Questao, Resposta, Tentativa


DISTRIBUICOES = {
    "reforco": {"básica": 4, "intermediária": 4, "avançada": 1},
    "equilibrado": {"básica": 3, "intermediária": 4, "avançada": 2},
    "desafio": {"básica": 2, "intermediária": 4, "avançada": 3},
}


def nivel_do_aluno(aluno, tema):
    media_tema = aluno.tentativas.filter(
        tema=tema, status__in=[Tentativa.Status.CONCLUIDA, Tentativa.Status.REVISAO]
    ).aggregate(m=Avg("nota_total"))["m"]
    if media_tema is None:
        media_tema = aluno.tentativas.filter(
            status__in=[Tentativa.Status.CONCLUIDA, Tentativa.Status.REVISAO]
        ).aggregate(m=Avg("nota_total"))["m"]
    if media_tema is None:
        return "equilibrado"
    media = Decimal(str(media_tema))
    if media < Decimal("6"):
        return "reforco"
    if media >= Decimal("8"):
        return "desafio"
    return "equilibrado"


def _priorizar_ineditas(aluno, questoes):
    respondidas = set(
        Resposta.objects.filter(tentativa__aluno=aluno, questao__in=questoes).values_list("questao_id", flat=True)
    )
    ineditas = [q for q in questoes if q.pk not in respondidas]
    repetidas = [q for q in questoes if q.pk in respondidas]
    random.SystemRandom().shuffle(ineditas)
    random.SystemRandom().shuffle(repetidas)
    return ineditas + repetidas


def selecionar_questoes(aluno, tema):
    nivel = nivel_do_aluno(aluno, tema)
    distribuicao = DISTRIBUICOES[nivel]
    objetivas = list(
        tema.questoes.filter(tipo=Questao.Tipo.OBJETIVA, status=Questao.Status.APROVADA)
    )
    discursivas = list(
        tema.questoes.filter(tipo=Questao.Tipo.DISCURSIVA, status=Questao.Status.APROVADA)
    )
    if len(objetivas) < 9 or not discursivas:
        return [], None, nivel

    por_dificuldade = defaultdict(list)
    for q in _priorizar_ineditas(aluno, objetivas):
        chave = (q.dificuldade or "intermediária").strip().lower()
        por_dificuldade[chave].append(q)

    escolhidas = []
    usados = set()
    for dificuldade, quantidade in distribuicao.items():
        for q in por_dificuldade.get(dificuldade, [])[:quantidade]:
            escolhidas.append(q)
            usados.add(q.pk)

    if len(escolhidas) < 9:
        for q in _priorizar_ineditas(aluno, objetivas):
            if q.pk not in usados:
                escolhidas.append(q)
                usados.add(q.pk)
                if len(escolhidas) == 9:
                    break

    discursiva = _priorizar_ineditas(aluno, discursivas)[0]
    random.SystemRandom().shuffle(escolhidas)
    return escolhidas[:9], discursiva, nivel
