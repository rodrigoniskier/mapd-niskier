import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from core.models import Questao

from .gemini import (
    DIRETRIZES_ENAMED_OBJETIVAS,
    DiscursivasLoteSchema,
    ObjetivasLoteSchema,
    _contexto_base_pacote,
    _fontes_aprovadas,
    _gerar_estruturado,
)


@dataclass
class QuestoesAdicionais:
    objetivas: list
    discursivas: list


def _normalizar(texto):
    texto = (texto or "").casefold()
    texto = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    return re.sub(r"\s+", " ", texto).strip()


def _tokens_relevantes(texto):
    return {token for token in _normalizar(texto).split() if len(token) >= 4}


def _muito_semelhante(texto_a, texto_b):
    a = _normalizar(texto_a)
    b = _normalizar(texto_b)
    if not a or not b:
        return False
    if a == b:
        return True

    sequencia = SequenceMatcher(None, a, b).ratio()
    tokens_a = _tokens_relevantes(a)
    tokens_b = _tokens_relevantes(b)
    if tokens_a and tokens_b:
        jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    else:
        jaccard = 0.0

    # Dois filtros complementares: frase muito parecida OU forte sobreposição lexical.
    # O limiar é deliberadamente alto para permitir avaliar o mesmo conteúdo por outra
    # situação clínica sem aceitar apenas uma paráfrase do item já existente.
    return sequencia >= 0.78 or (min(len(tokens_a), len(tokens_b)) >= 12 and jaccard >= 0.68)


def _texto_questao_schema(questao):
    if hasattr(questao, "enunciado_completo"):
        return questao.enunciado_completo()
    return questao.enunciado


def _validar_lote_inedito(questoes, corpus):
    novos = []
    for questao in questoes:
        texto = _texto_questao_schema(questao)
        if any(_muito_semelhante(texto, anterior) for anterior in corpus + novos):
            return False
        novos.append(texto)
    return True


def _corpus_existente(tema):
    return list(
        tema.questoes.exclude(enunciado="").values_list("enunciado", flat=True)
    )


def _resumo_banco(tema, max_chars=18000):
    """Resumo compacto para orientar o Gemini sem inflar excessivamente o prompt."""
    linhas = []
    usados = 0
    for questao in tema.questoes.order_by("-id").only("id", "tipo", "enunciado"):
        resumo = re.sub(r"\s+", " ", questao.enunciado).strip()[:260]
        linha = f"- #{questao.pk} [{questao.tipo}] {resumo}\n"
        if usados + len(linha) > max_chars:
            break
        linhas.append(linha)
        usados += len(linha)
    return "".join(linhas) or "- Banco ainda vazio."


def _gerar_lote_objetivas(base, resumo_banco, corpus, numero_lote, distribuicao):
    basicas, intermediarias, avancadas = distribuicao
    for rodada in range(1, 5):
        lote, _ = _gerar_estruturado(
            f"""
{base}

{DIRETRIZES_ENAMED_OBJETIVAS}

Gere o lote adicional {numero_lote} de 3, com exatamente 5 questões objetivas NOVAS.
Distribuição obrigatória: {basicas} básicas, {intermediarias} intermediárias e {avancadas} avançada(s).

REGRA DE INEDITISMO OBRIGATÓRIA:
- nenhuma questão pode repetir ou apenas parafrasear uma questão já existente;
- não reutilize a mesma vinheta clínica trocando somente idade, sexo, nome ou um dado isolado;
- varie cenário, combinação de achados, evidência diagnóstica, mecanismo central e decisão solicitada;
- o mesmo conteúdo pode ser avaliado novamente, mas por uma situação-problema e um percurso de raciocínio diferentes;
- também não repita questões produzidas nos lotes desta mesma solicitação.

BANCO JÁ EXISTENTE — USE APENAS PARA EVITAR REPETIÇÃO:
{resumo_banco}

Requisitos:
- preencha `texto_base` e `enunciado` separadamente;
- cinco alternativas A–E, com uma única resposta correta;
- em `nivel_cognitivo`, use exatamente: lembrar, compreender, aplicar, analisar ou avaliar;
- em `alinhamento_enamed`, registre área, perfil, competência e domínio mobilizados;
- em `justificativa`, use linhas A — CERTA/ERRADA até E, justificando cada opção;
- não produza slides nem questões discursivas nesta resposta.

Esta é a rodada anti-duplicação {rodada}. Se um caso do banco parecer semelhante ao que você planejou,
descarte-o e crie outro antes de responder.
""",
            ObjetivasLoteSchema,
            8000,
        )
        if _validar_lote_inedito(lote.objetivas, corpus):
            return lote.objetivas
    raise RuntimeError(
        "Não foi possível garantir cinco objetivas suficientemente distintas do banco atual. "
        "Tente novamente para que a IA proponha novos cenários."
    )


def _gerar_discursivas(base, resumo_banco, corpus):
    for rodada in range(1, 5):
        lote, _ = _gerar_estruturado(
            f"""
{base}

Produza exatamente 2 questões discursivas NOVAS.
Cada questão deve apresentar um resumo clínico com 3 a 5 erros conceituais discretos para o aluno
identificar, explicar e corrigir. Não revele os erros no enunciado. Inclua espelho detalhado,
habilidade e referências.

REGRA DE INEDITISMO OBRIGATÓRIA:
- não repita nem parafraseie questões já existentes;
- não reutilize a mesma vinheta clínica apenas alterando detalhes superficiais;
- varie cenário, mecanismo, achados e erros conceituais propositais;
- podem abordar o mesmo conteúdo, desde que exijam outro percurso de análise.

BANCO JÁ EXISTENTE — USE APENAS PARA EVITAR REPETIÇÃO:
{resumo_banco}

Esta é a rodada anti-duplicação {rodada}.
Não produza slides nem questões objetivas nesta resposta.
""",
            DiscursivasLoteSchema,
            5000,
        )
        if _validar_lote_inedito(lote.discursivas, corpus):
            return lote.discursivas
    raise RuntimeError(
        "Não foi possível garantir duas discursivas suficientemente distintas do banco atual. "
        "Tente novamente para que a IA proponha novos cenários."
    )


def gerar_questoes_adicionais(tema):
    """Gera 15 objetivas e 2 discursivas sem substituir o banco já existente."""
    contexto, urls = _fontes_aprovadas(max_chars=22000)
    base = _contexto_base_pacote(tema, contexto, urls)
    resumo_banco = _resumo_banco(tema)
    corpus = _corpus_existente(tema)

    distribuicoes = [
        (2, 2, 1),
        (2, 2, 1),
        (1, 3, 1),
    ]
    objetivas = []

    for numero_lote, distribuicao in enumerate(distribuicoes, start=1):
        novas = _gerar_lote_objetivas(
            base,
            resumo_banco,
            corpus,
            numero_lote,
            distribuicao,
        )
        objetivas.extend(novas)
        corpus.extend(_texto_questao_schema(q) for q in novas)
        resumo_banco += "".join(
            f"- [NOVA OBJETIVA] {_texto_questao_schema(q)[:260]}\n" for q in novas
        )

    discursivas = _gerar_discursivas(base, resumo_banco, corpus)
    return QuestoesAdicionais(objetivas=objetivas, discursivas=discursivas)
