import json
import logging
import time
from decimal import Decimal
from typing import Literal

from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field, field_validator

from core.models import FonteConhecimento, Questao, Tentativa

logger = logging.getLogger(__name__)


class SlideSchema(BaseModel):
    ordem: int = Field(ge=1, le=3)
    titulo: str = Field(min_length=5, max_length=160)
    conteudo: str = Field(min_length=120, max_length=2200)
    pontos_chave: list[str] = Field(default_factory=list, min_length=2, max_length=6)


class FonteSchema(BaseModel):
    titulo: str
    url: str
    resumo: str = ""


class AlternativasSchema(BaseModel):
    """Objeto fechado para evitar `additionalProperties` no schema enviado ao Gemini."""

    A: str = Field(min_length=1, max_length=1200)
    B: str = Field(min_length=1, max_length=1200)
    C: str = Field(min_length=1, max_length=1200)
    D: str = Field(min_length=1, max_length=1200)
    E: str = Field(min_length=1, max_length=1200)

    @field_validator("A", "B", "C", "D", "E")
    @classmethod
    def validar_texto(cls, valor):
        texto = str(valor).strip()
        if not texto:
            raise ValueError("Alternativas vazias não são permitidas.")
        return texto


class QuestaoObjetivaSchema(BaseModel):
    enunciado: str = Field(min_length=120)
    alternativas: AlternativasSchema
    gabarito: Literal["A", "B", "C", "D", "E"]
    justificativa: str = Field(min_length=80)
    dificuldade: Literal["básica", "intermediária", "avançada"]
    nivel_cognitivo: str
    habilidade: str
    referencias: list[FonteSchema] = Field(default_factory=list)

    def alternativas_dict(self):
        return self.alternativas.model_dump()


class QuestaoDiscursivaSchema(BaseModel):
    enunciado: str = Field(min_length=150)
    erros_propositais: list[str] = Field(min_length=3, max_length=5)
    justificativa: str = Field(min_length=150)
    habilidade: str
    referencias: list[FonteSchema] = Field(default_factory=list)


class PacoteEstudoSchema(BaseModel):
    slides: list[SlideSchema] = Field(min_length=2, max_length=3)
    objetivas: list[QuestaoObjetivaSchema] = Field(min_length=9, max_length=18)
    discursivas: list[QuestaoDiscursivaSchema] = Field(min_length=1, max_length=3)


class CorrecaoDiscursivaSchema(BaseModel):
    nota: float = Field(ge=0, le=2.8)
    comentario: str = Field(min_length=80, max_length=3000)
    pontos_identificados: list[str] = Field(default_factory=list)
    pontos_omitidos: list[str] = Field(default_factory=list)
    precisa_revisao_docente: bool = False


class RespostaTutorSchema(BaseModel):
    resposta: str = Field(min_length=20, max_length=5000)
    fontes: list[FonteSchema] = Field(default_factory=list)
    nivel_pista: int = Field(default=0, ge=0, le=3)


class FeedbackSchema(BaseModel):
    texto: str = Field(min_length=100, max_length=10000)


def _client():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY não configurada.")
    from google import genai
    from google.genai import types

    try:
        return genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(settings.GEMINI_TIMEOUT * 1000)),
        )
    except TypeError:
        return genai.Client(api_key=settings.GEMINI_API_KEY)


def _fontes_aprovadas(max_chars=30000):
    fontes = FonteConhecimento.objects.filter(aprovada=True).order_by("-principal", "titulo")
    blocos = []
    urls = []
    usados = 0
    for fonte in fontes:
        if fonte.url and fonte.permitir_contexto_url:
            urls.append(fonte.url)
        conteudo = fonte.conteudo.strip()
        bloco = (
            f"\nFONTE APROVADA: {fonte.titulo}\n"
            f"TIPO: {fonte.get_tipo_display()}\n"
            f"URL: {fonte.url or 'não informada'}\n"
            f"RESUMO DE AUDITORIA: {fonte.resumo_auditoria or 'não informado'}\n"
            f"CONTEÚDO DISPONÍVEL:\n{conteudo}\n"
        )
        if usados + len(bloco) > max_chars:
            restante = max_chars - usados
            if restante > 500:
                blocos.append(bloco[:restante])
            break
        blocos.append(bloco)
        usados += len(bloco)
    return "\n".join(blocos), list(dict.fromkeys(urls))[:20]


def _config_estruturada(schema, max_tokens, tools=None):
    from google.genai import types

    kwargs = {
        "response_mime_type": "application/json",
        "response_schema": schema,
        "max_output_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
    return types.GenerateContentConfig(**kwargs)


def _gerar_estruturado(prompt, schema, max_tokens, tools=None):
    modelos = [settings.GEMINI_MODEL]
    fallback = getattr(settings, "GEMINI_FALLBACK_MODEL", "")
    if fallback and fallback not in modelos:
        modelos.append(fallback)
    ultimo_erro = None
    for modelo in modelos:
        for tentativa in range(2):
            try:
                response = _client().models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=_config_estruturada(schema, max_tokens, tools=tools),
                )
                if not response.text:
                    raise RuntimeError("O Gemini retornou uma resposta vazia.")
                return schema.model_validate_json(response.text), response
            except Exception as exc:
                ultimo_erro = exc
                logger.warning("Falha Gemini modelo=%s tentativa=%s: %s", modelo, tentativa + 1, exc)
                time.sleep(1 + tentativa)
                if tools:
                    tools = None
    raise RuntimeError(f"Não foi possível obter resposta válida do Gemini: {ultimo_erro}")


def _fontes_grounding(response):
    fontes = []
    try:
        candidato = response.candidates[0]
        metadata = candidato.grounding_metadata
        chunks = getattr(metadata, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if web and getattr(web, "uri", None):
                fontes.append(
                    {
                        "titulo": getattr(web, "title", None) or "Fonte externa",
                        "url": web.uri,
                        "resumo": "Fonte recuperada pelo embasamento da Pesquisa Google.",
                    }
                )
    except Exception:
        pass
    vistos = set()
    resultado = []
    for fonte in fontes:
        if fonte["url"] not in vistos:
            vistos.add(fonte["url"])
            resultado.append(fonte)
    return resultado


def gerar_pacote_estudo(tema):
    contexto, urls = _fontes_aprovadas()
    url_bloco = "\n".join(f"- {url}" for url in urls)
    prompt = f"""
Você é a IA Niskier, assistente acadêmica do curso de Medicina. Crie um pacote auditável de estudo
para o tema: {tema.titulo}.

Objetivo pedagógico:
- revisão rápida em 2 ou 3 telas;
- prática deliberada personalizada;
- avaliação formativa contextualizada, com feedback construtivo;
- integração entre mecanismos básicos, evidências diagnósticas e raciocínio clínico.

Regras obrigatórias para os slides:
- produza exatamente 3 slides;
- cada slide deve ser curto, clinicamente relevante e mecanístico;
- use linguagem adequada ao 4º período de Medicina;
- inclua de 2 a 6 pontos-chave em cada slide.

Regras obrigatórias para o banco de questões:
- produza exatamente 15 questões objetivas no padrão ENAMED, com situação-problema ou cenário clínico;
- cinco alternativas A–E, homogêneas, plausíveis e com apenas uma resposta defensável;
- em `alternativas`, preencha obrigatoriamente os cinco campos fixos A, B, C, D e E;
- evite pistas gramaticais, absolutismos, negativas desnecessárias, pegadinhas e memorização isolada;
- distribuição: 5 básicas, 7 intermediárias e 3 avançadas;
- registre habilidade avaliada, nível cognitivo, justificativa do gabarito e referências;
- produza exatamente 2 questões discursivas com resumo clínico contendo 3 a 5 erros conceituais discretos;
- o aluno deverá identificar, explicar e corrigir os erros;
- não inclua o gabarito no enunciado;
- não invente números, recomendações ou referências.

Regras de fonte:
- baseie-se prioritariamente na fonte principal e nas fontes aprovadas;
- URLs públicas aprovadas podem ser lidas pela ferramenta de contexto de URL;
- toda questão deve apontar pelo menos uma fonte real;
- escreva em português do Brasil.

Instruções adicionais do professor:
{tema.instrucoes_ia or 'Nenhuma.'}

URLS APROVADAS:
{url_bloco or '- Nenhuma URL cadastrada.'}

TRECHOS E RESUMOS APROVADOS:
{contexto or 'Nenhum conteúdo textual importado. Use apenas as URLs aprovadas.'}
"""
    tools = [{"url_context": {}}] if urls else None
    pacote, _ = _gerar_estruturado(prompt, PacoteEstudoSchema, 24000, tools=tools)
    return pacote


def responder_tutor(tema, mensagem, historico="", contexto_questao="", nivel_pista=1, modo_questao=False):
    contexto, urls = _fontes_aprovadas(22000)
    regras_modo = """
Você está no modo tutor de avaliação. É proibido:
- informar a letra ou o texto da alternativa correta;
- confirmar diretamente que uma alternativa específica é correta;
- eliminar alternativas até restar apenas uma;
- resolver integralmente a questão pelo aluno.
Ofereça uma pista proporcional ao nível solicitado:
1 = indique o conceito central e faça uma pergunta-guia;
2 = conecte os dados clínicos ao mecanismo e sugira uma comparação;
3 = ajude a testar o raciocínio do aluno, sem revelar a resposta.
""" if modo_questao else """
Você está no Plantão Niskier 24h. Responda à dúvida com clareza, integração clínico-mecanística e
linguagem acadêmica. Pode explicar diretamente conceitos, mas estimule o aluno a conferir a fonte.
"""
    prompt = f"""
Você é a IA Niskier, tutora acadêmica de Mecanismos de Agressão, Patológicos e de Defesa.
Tema: {tema.titulo}

{regras_modo}

Pergunta do aluno:
{mensagem}

Contexto da questão, quando houver:
{contexto_questao}

Histórico recente:
{historico}

Regras gerais:
- priorize a fonte principal e as fontes aprovadas;
- quando precisar aprofundar além do material, use fontes científicas, governamentais ou institucionais;
- para cada fonte externa, informe título, URL e resumo curto para auditoria;
- declare incerteza quando a evidência não for suficiente;
- não invente referências;
- resposta entre 120 e 700 palavras, salvo se a dúvida exigir menos;
- escreva em português do Brasil.

FONTES APROVADAS:
{contexto}
"""
    tools = [{"url_context": {}}]
    if tema.permitir_fontes_externas and getattr(settings, "GEMINI_ENABLE_SEARCH", True):
        tools.append({"google_search": {}})
    resposta, raw = _gerar_estruturado(prompt, RespostaTutorSchema, 4000, tools=tools)
    fontes = [f.model_dump() for f in resposta.fontes]
    fontes.extend(_fontes_grounding(raw))
    unicas = []
    vistos = set()
    for fonte in fontes:
        url = fonte.get("url", "")
        if url and url not in vistos:
            vistos.add(url)
            unicas.append(fonte)
    resposta.fontes = [FonteSchema(**f) for f in unicas[:8]]
    resposta.nivel_pista = nivel_pista if modo_questao else 0
    return resposta


def corrigir_discursiva(questao, resposta_aluno):
    prompt = f"""
Corrija uma resposta discursiva formativa de Medicina de 0 a 2,8 pontos.

ENUNCIADO:
{questao.enunciado}

ERROS ESPERADOS:
{json.dumps(questao.erros_propositais, ensure_ascii=False)}

ESPELHO DO PROFESSOR:
{questao.justificativa}

RESPOSTA DO ALUNO:
{resposta_aluno}

Rubrica:
- identificação dos erros: 35%;
- explicação do motivo: 25%;
- correção conceitual: 25%;
- integração clínico-mecanística e clareza: 15%.
Se a resposta for ambígua, incompleta ou não puder ser corrigida com confiança, marque
precisa_revisao_docente=true. Não atribua conteúdo que o aluno não escreveu.
"""
    correcao, _ = _gerar_estruturado(prompt, CorrecaoDiscursivaSchema, 2500)
    return correcao


def feedback_deterministico(tentativa: Tentativa):
    linhas = [
        f"Resultado geral: {tentativa.nota_total}/10,0 no tema {tentativa.tema.titulo}.",
        f"Questões objetivas: {tentativa.nota_objetiva}/7,2. Questão discursiva: {tentativa.nota_discursiva}/2,8.",
    ]
    for item in tentativa.itens.select_related("questao").all():
        q = item.questao
        r = tentativa.respostas.filter(questao=q).first()
        if q.tipo == Questao.Tipo.OBJETIVA:
            situacao = "correta" if r and r.correta else "incorreta ou não respondida"
            linhas.append(
                f"Questão {item.ordem}: resposta {situacao}. {q.justificativa or 'Revise o mecanismo central avaliado.'}"
            )
        else:
            linhas.append(
                f"Questão {item.ordem} discursiva: nota {r.nota if r else 0}/2,8. "
                f"{r.comentario if r else 'Aguardando correção.'}"
            )
    if tentativa.quantidade_pistas:
        linhas.append(
            f"Você utilizou {tentativa.quantidade_pistas} pista(s). Refaça mentalmente as questões antes de consultar o gabarito comentado."
        )
    linhas.append("Prioridade de revisão: retome os conceitos das questões incorretas e explique-os com suas próprias palavras.")
    return "\n\n".join(linhas)[:10000]


def gerar_feedback(tentativa: Tentativa):
    dados = []
    for item in tentativa.itens.select_related("questao"):
        q = item.questao
        r = tentativa.respostas.filter(questao=q).first()
        dados.append(
            {
                "ordem": item.ordem,
                "tipo": q.tipo,
                "habilidade": q.habilidade,
                "dificuldade": q.dificuldade,
                "resposta": (r.alternativa_marcada or r.resposta_textual) if r else "",
                "correta": r.correta if r else None,
                "nota": str(r.nota if r else 0),
                "comentario_correcao": r.comentario if r else "",
                "justificativa": q.justificativa,
            }
        )
    prompt = f"""
Gere um feedback individual, construtivo e auditável para uma avaliação formativa de Medicina.
Limite absoluto de 10.000 caracteres. Comente cada uma das 10 questões, identifique padrões de
erro, reconheça pontos fortes e proponha uma sequência curta de revisão. Não invente respostas.
Não use tom punitivo. Não entregue apenas a nota.

Aluno: {tentativa.aluno.nome_exibicao}
Tema: {tentativa.tema.titulo}
Nota: {tentativa.nota_total}/10
Pistas utilizadas: {tentativa.quantidade_pistas}
Dados das questões:
{json.dumps(dados, ensure_ascii=False)}
"""
    resultado, _ = _gerar_estruturado(prompt, FeedbackSchema, 6000)
    return resultado.texto[:10000]
