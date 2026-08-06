import json
from decimal import Decimal
from typing import Literal
from django.conf import settings
from pydantic import BaseModel, Field
from core.models import FonteConhecimento, Questao, Resposta, Tentativa


class SlideSchema(BaseModel):
    ordem: int = Field(ge=1, le=3)
    titulo: str
    conteudo: str


class QuestaoObjetivaSchema(BaseModel):
    enunciado: str
    alternativas: dict[str, str]
    gabarito: Literal["A", "B", "C", "D", "E"]
    justificativa: str
    dificuldade: Literal["básica", "intermediária", "avançada"]
    nivel_cognitivo: str


class QuestaoDiscursivaSchema(BaseModel):
    enunciado: str
    erros_propositais: list[str]
    justificativa: str


class PacoteEstudoSchema(BaseModel):
    slides: list[SlideSchema]
    objetivas: list[QuestaoObjetivaSchema]
    discursiva: QuestaoDiscursivaSchema


class CorrecaoDiscursivaSchema(BaseModel):
    nota: float = Field(ge=0, le=2.8)
    comentario: str


class FonteRespostaSchema(BaseModel):
    titulo: str
    url: str
    resumo: str


class RespostaTutorSchema(BaseModel):
    resposta: str
    fontes: list[FonteRespostaSchema] = Field(default_factory=list)


def _client():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada.")
    from google import genai
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _fontes_contexto(max_chars=24000):
    fontes = FonteConhecimento.objects.filter(aprovada=True).order_by("-principal", "titulo")
    partes = []
    usados = 0
    for fonte in fontes:
        bloco = f"\nFONTE: {fonte.titulo}\nURL: {fonte.url}\nCONTEÚDO:\n{fonte.conteudo}\n"
        if usados + len(bloco) > max_chars:
            restante = max_chars - usados
            if restante > 500:
                partes.append(bloco[:restante])
            break
        partes.append(bloco)
        usados += len(bloco)
    return "\n".join(partes)


def gerar_pacote_estudo(tema):
    from google.genai import types

    prompt = f"""
Você é a IA Niskier, assistente acadêmica de Medicina.
Crie um pacote de estudo para o tema: {tema.titulo}

Regras:
- Baseie-se prioritariamente nas fontes fornecidas.
- Produza exatamente 3 slides de revisão rápida, cada um curto, clínico e mecanístico.
- Produza exatamente 9 questões objetivas no padrão ENAMED, contextualizadas, com cinco alternativas A-E.
- Apenas uma alternativa pode ser correta.
- Distribuição: 3 básicas, 4 intermediárias e 2 avançadas.
- Evite pistas gramaticais, negativas desnecessárias e alternativas heterogêneas.
- Produza 1 questão discursiva com um resumo clínico contendo de 3 a 5 erros conceituais discretos.
- Na discursiva, o aluno deverá identificar, explicar e corrigir os erros.
- Não invente diretrizes, números ou referências não presentes nas fontes.
- Escreva em português do Brasil.

FONTES APROVADAS:
{_fontes_contexto()}
"""
    response = _client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PacoteEstudoSchema,
            temperature=0.35,
            max_output_tokens=16000,
        ),
    )
    return PacoteEstudoSchema.model_validate_json(response.text)


def responder_tutor(tema, mensagem, historico="", contexto_questao=""):
    from google.genai import types

    prompt = f"""
Você é a IA Niskier, tutora socrática de Medicina.
Tema: {tema.titulo}
Contexto da questão, quando houver:
{contexto_questao}

Mensagem do aluno:
{mensagem}

Histórico recente:
{historico}

Regras obrigatórias:
- Não dê diretamente a alternativa correta nem entregue a resposta pronta.
- Não elimine alternativas até sobrar apenas uma.
- Ajude por perguntas, pistas graduais e encadeamento de raciocínio.
- Comece pelo dado clínico ou mecanismo mais relevante.
- Corrija equívocos com respeito e precisão.
- Use as fontes aprovadas abaixo.
- Só cite URLs presentes nas fontes aprovadas.
- Quando citar, inclua título, URL e resumo breve para auditoria.
- Resposta objetiva, geralmente entre 150 e 500 palavras.

FONTES APROVADAS:
{_fontes_contexto(18000)}
"""
    response = _client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RespostaTutorSchema,
            temperature=0.35,
            max_output_tokens=1800,
        ),
    )
    return RespostaTutorSchema.model_validate_json(response.text)


def corrigir_discursiva(questao, resposta_aluno):
    from google.genai import types
    prompt = f"""
Corrija uma resposta discursiva de Medicina de 0 a 2,8 pontos.

ENUNCIADO:
{questao.enunciado}

ERROS ESPERADOS:
{json.dumps(questao.erros_propositais, ensure_ascii=False)}

ESPELHO:
{questao.justificativa}

RESPOSTA DO ALUNO:
{resposta_aluno}

Critérios:
- identificação dos erros;
- explicação do motivo;
- correção conceitual;
- integração clínico-mecanística;
- clareza.
Se a resposta for ambígua, seja conservador e sinalize necessidade de revisão docente.
"""
    response = _client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CorrecaoDiscursivaSchema,
            temperature=0.15,
            max_output_tokens=1500,
        ),
    )
    return CorrecaoDiscursivaSchema.model_validate_json(response.text)


def gerar_feedback(tentativa: Tentativa):
    linhas = []
    for item in tentativa.itens.select_related("questao").all():
        q = item.questao
        r = tentativa.respostas.filter(questao=q).first()
        if q.tipo == Questao.Tipo.OBJETIVA:
            linhas.append(
                f"Q{item.ordem}: marcada={r.alternativa_marcada if r else 'sem resposta'}; "
                f"gabarito={q.gabarito}; correta={r.correta if r else False}; "
                f"justificativa={q.justificativa}"
            )
        else:
            linhas.append(
                f"Q{item.ordem} discursiva: resposta={r.resposta_textual if r else ''}; "
                f"nota={r.nota if r else 0}; comentário={r.comentario if r else ''}"
            )

    prompt = f"""
Gere feedback individual de uma avaliação formativa de Medicina.
Limite absoluto: 10.000 caracteres.
Comente cada questão, os padrões de acerto/erro, pontos fortes e prioridades de revisão.
Não humilhe o aluno. Não invente respostas que não constem abaixo.
Tema: {tentativa.tema.titulo}
Nota: {tentativa.nota_total}/10
Dados:
{chr(10).join(linhas)}
"""
    response = _client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config={"temperature": 0.25, "max_output_tokens": 3500},
    )
    return (response.text or "")[:10000]
