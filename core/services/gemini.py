import json
import logging
import re
import time
from typing import Literal

from django.conf import settings
from pydantic import BaseModel, Field, field_validator, model_validator

from core.models import FonteConhecimento, Questao, Tentativa

logger = logging.getLogger(__name__)


DIRETRIZES_ENAMED_OBJETIVAS = """
PADRÃO DE CONSTRUÇÃO DA QUESTÃO — PROJETO QUESTÕES-ENAMED

1. PARAMETRIZAÇÃO PEDAGÓGICA
- Defina para cada item a área principal e, quando pertinente, uma área secundária.
- Alinhe o item a um perfil do avaliado, a uma competência e a um domínio de conteúdo
  pertinentes ao ENAMED/DCNs, sem apenas repetir o nome do tema.
- Use a Taxonomia de Bloom de forma coerente com a dificuldade: questões básicas podem
  mobilizar compreensão e aplicação simples; intermediárias devem priorizar aplicação e
  análise; avançadas devem exigir análise ou avaliação.
- A dificuldade deve decorrer do raciocínio necessário, e não de obscuridade, excesso de
  dados, vocabulário raro ou alternativas ambíguas.

2. TEXTO-BASE
- Deve funcionar como motivador, caso clínico ou situação-estímulo.
- Deve ser curto, claro, suficiente e indispensável para resolver o item.
- O estudante não deve conseguir responder corretamente ignorando o texto-base.
- Inclua somente dados relevantes e apresente-os em ordem clínica ou lógica.
- Textos, tabelas, resultados, gráficos ou figuras devem ter referência quando utilizados.
- Não revele a resposta nem introduza pistas lexicais para o gabarito.

3. ENUNCIADO/COMANDO
- Deve conter uma única tarefa, direta, clara e objetiva.
- Não deve acrescentar dados novos ao texto-base.
- Evite comandos negativos, especialmente “não”, “exceto”, “incorreta” ou “errada”.
- O comando deve ser respondido pelas alternativas e estar alinhado ao nível de Bloom.

4. ALTERNATIVAS
- Nesta plataforma MAPD, produza cinco alternativas A–E e apenas uma correta.
- O gabarito deve ser único, inequívoco e defensável à luz das fontes.
- Distratores devem ser plausíveis e representar erros conceituais, interpretações ou
  condutas que um estudante real poderia adotar; não use pegadinhas.
- Mantenha paralelismo sintático e semântico entre todas as opções.
- Use extensão semelhante ou ordem lógica; não deixe o gabarito sistematicamente mais
  completo, específico ou longo.
- Evite repetição desnecessária do enunciado, pistas gramaticais, discordância, categorias
  misturadas e sobreposição entre opções.
- Não use “todas as anteriores”, “nenhuma das anteriores” ou combinações de alternativas.
- Evite termos absolutos como “sempre”, “nunca”, “todos”, “apenas” e “somente”, salvo
  quando forem cientificamente indispensáveis e igualmente plausíveis no conjunto.

5. JUSTIFICATIVA E AUDITORIA
- Justifique cada alternativa separadamente.
- Use exatamente o formato “A — CERTA:” ou “A — ERRADA:” e repita para B, C, D e E.
- Explique por que o gabarito está correto e qual erro torna cada distrator incorreto.
- Vincule a justificativa aos dados do texto-base, ao mecanismo e às fontes; não faça
  justificativas circulares nem apenas repita a alternativa.
- Registre habilidade observável, nível de Bloom e referências reais.
""".strip()


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
    """Objeto fechado para as cinco alternativas exigidas pela avaliação MAPD."""

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

    @model_validator(mode="after")
    def validar_conjunto(self):
        valores = [self.A, self.B, self.C, self.D, self.E]
        normalizados = [re.sub(r"\s+", " ", valor.casefold()).strip() for valor in valores]
        if len(set(normalizados)) != 5:
            raise ValueError("As cinco alternativas devem ser distintas.")

        proibidas = (
            "todas as anteriores",
            "todas as alternativas anteriores",
            "nenhuma das anteriores",
            "nenhuma das alternativas anteriores",
        )
        if any(expressao in alternativa for alternativa in normalizados for expressao in proibidas):
            raise ValueError("Não use 'todas/nenhuma das anteriores'.")
        return self


class QuestaoObjetivaSchema(BaseModel):
    texto_base: str = Field(min_length=120, max_length=2800)
    enunciado: str = Field(min_length=20, max_length=500)
    alternativas: AlternativasSchema
    gabarito: Literal["A", "B", "C", "D", "E"]
    justificativa: str = Field(min_length=240, max_length=7000)
    dificuldade: Literal["básica", "intermediária", "avançada"]
    nivel_cognitivo: Literal["lembrar", "compreender", "aplicar", "analisar", "avaliar"]
    habilidade: str = Field(min_length=20, max_length=1200)
    alinhamento_enamed: str = Field(min_length=30, max_length=1600)
    referencias: list[FonteSchema] = Field(default_factory=list)

    @field_validator("enunciado")
    @classmethod
    def validar_comando_positivo(cls, valor):
        texto = str(valor).strip()
        if re.search(r"\b(não|exceto|incorreta|errada)\b", texto, flags=re.IGNORECASE):
            raise ValueError("O enunciado deve evitar formulação negativa.")
        return texto

    @model_validator(mode="after")
    def validar_justificativa_por_alternativa(self):
        texto = self.justificativa.upper()
        rotulos = {}
        for letra in "ABCDE":
            encontrado = re.search(
                rf"(?:^|\n)\s*{letra}\s*[—–\-:)]*\s*(CERTA|ERRADA)\s*:",
                texto,
            )
            if not encontrado:
                raise ValueError(
                    "A justificativa deve identificar A–E como CERTA ou ERRADA."
                )
            rotulos[letra] = encontrado.group(1)

        if rotulos[self.gabarito] != "CERTA":
            raise ValueError("O gabarito deve estar identificado como CERTA na justificativa.")
        if any(
            classificacao != ("CERTA" if letra == self.gabarito else "ERRADA")
            for letra, classificacao in rotulos.items()
        ):
            raise ValueError("Apenas o gabarito pode estar identificado como CERTA.")
        return self

    def alternativas_dict(self):
        return self.alternativas.model_dump()

    def enunciado_completo(self):
        return f"{self.texto_base.strip()}\n\n{self.enunciado.strip()}"

    def referencias_registro(self):
        referencias = [fonte.model_dump() for fonte in self.referencias]
        referencias.append(
            {
                "titulo": "Alinhamento ENAMED/DCNs",
                "url": "",
                "resumo": self.alinhamento_enamed.strip(),
            }
        )
        return referencias


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


class SlidesLoteSchema(BaseModel):
    slides: list[SlideSchema] = Field(min_length=3, max_length=3)


class ObjetivasLoteSchema(BaseModel):
    objetivas: list[QuestaoObjetivaSchema] = Field(min_length=5, max_length=5)


class DiscursivasLoteSchema(BaseModel):
    discursivas: list[QuestaoDiscursivaSchema] = Field(min_length=2, max_length=2)


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


def _config_estruturada(max_tokens, tools=None, usar_json_mode=True):
    """Monta a configuração sem enviar JSON Schema ao endpoint Gemini."""
    from google.genai import types

    kwargs = {
        "max_output_tokens": max_tokens,
        "temperature": 0.2,
    }
    if usar_json_mode:
        kwargs["response_mime_type"] = "application/json"
    if tools:
        kwargs["tools"] = tools
    return types.GenerateContentConfig(**kwargs)


def _limpar_json_resposta(texto):
    texto = (texto or "").strip().lstrip("\ufeff")
    if texto.startswith("```"):
        linhas = texto.splitlines()
        if linhas and linhas[0].strip().startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].strip() == "```":
            linhas = linhas[:-1]
        texto = "\n".join(linhas).strip()

    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio >= 0 and fim > inicio:
        texto = texto[inicio : fim + 1]
    return texto


def _validar_json_resposta(texto, schema):
    texto = _limpar_json_resposta(texto)
    if not texto:
        raise RuntimeError("O Gemini retornou uma resposta vazia.")

    try:
        return schema.model_validate_json(texto)
    except Exception as erro_original:
        reparado = re.sub(r",\s*([}\]])", r"\1", texto)
        try:
            dados = json.loads(reparado)
            return schema.model_validate(dados)
        except Exception:
            raise erro_original


def _modelos_configurados():
    modelos = []
    for valor in (
        getattr(settings, "GEMINI_MODEL", ""),
        getattr(settings, "GEMINI_FALLBACK_MODEL", ""),
    ):
        modelo = (valor or "").strip()
        if modelo and modelo not in modelos:
            modelos.append(modelo)
    if not modelos:
        raise RuntimeError("Nenhum modelo Gemini foi configurado.")
    return modelos


def _gerar_estruturado(prompt, schema, max_tokens, tools=None):
    schema_texto = json.dumps(
        schema.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    prompt_json = (
        f"{prompt}\n\n"
        "FORMATO DE SAÍDA OBRIGATÓRIO:\n"
        "- retorne somente um objeto JSON válido;\n"
        "- não use Markdown, comentários ou texto fora do JSON;\n"
        "- não encerre a resposta antes de fechar todos os objetos e listas;\n"
        "- respeite exatamente a estrutura e os campos deste contrato:\n"
        f"{schema_texto}"
    )

    erros = []
    planos = []
    if tools:
        planos.append((tools, True, "json+ferramentas"))
    planos.extend(
        [
            (None, True, "json"),
            (None, False, "texto-json"),
        ]
    )

    for modelo in _modelos_configurados():
        for ferramentas, usar_json_mode, modo in planos:
            for tentativa in range(1, 3):
                client = None
                try:
                    client = _client()
                    response = client.models.generate_content(
                        model=modelo,
                        contents=prompt_json,
                        config=_config_estruturada(
                            max_tokens,
                            tools=ferramentas,
                            usar_json_mode=usar_json_mode,
                        ),
                    )
                    resultado = _validar_json_resposta(
                        getattr(response, "text", ""),
                        schema,
                    )
                    return resultado, response
                except Exception as exc:
                    detalhe = f"{modelo}/{modo}/tentativa-{tentativa}: {exc}"
                    erros.append(detalhe)
                    logger.warning("Falha Gemini %s", detalhe)
                    time.sleep(2 * tentativa)
                finally:
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            logger.debug(
                                "Não foi possível fechar o cliente Gemini.",
                                exc_info=True,
                            )

    resumo = " | ".join(erros[-8:])
    raise RuntimeError(f"Não foi possível obter resposta válida do Gemini: {resumo}")


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


def _contexto_base_pacote(tema, contexto, urls):
    url_bloco = "\n".join(f"- {url}" for url in urls)
    return f"""
Você é a IA Niskier, assistente acadêmica do curso de Medicina.
Tema: {tema.titulo}.

Objetivos pedagógicos:
- revisão rápida e mecanística;
- prática deliberada personalizada;
- avaliação formativa contextualizada;
- integração entre mecanismos básicos, evidências diagnósticas e raciocínio clínico.

Regras gerais:
- linguagem adequada ao 4º período de Medicina;
- baseie-se prioritariamente na fonte principal e nas fontes aprovadas abaixo;
- não invente números, recomendações ou referências;
- escreva em português do Brasil;
- registre referências reais em cada questão.

Instruções adicionais do professor:
{tema.instrucoes_ia or 'Nenhuma.'}

URLS APROVADAS:
{url_bloco or '- Nenhuma URL cadastrada.'}

TRECHOS E RESUMOS APROVADOS:
{contexto or 'Nenhum conteúdo textual importado. Use conhecimento médico consolidado e cite apenas as URLs aprovadas.'}
"""


def gerar_pacote_estudo(tema):
    """Gera o pacote em cinco respostas menores para evitar truncamento e timeout."""
    contexto, urls = _fontes_aprovadas(max_chars=22000)
    base = _contexto_base_pacote(tema, contexto, urls)

    slides_lote, _ = _gerar_estruturado(
        f"""
{base}

Produza exatamente 3 telas de revisão.
Cada tela deve conter título, texto mecanístico clinicamente relevante e de 2 a 6 pontos-chave.
Não produza questões nesta resposta.
""",
        SlidesLoteSchema,
        3500,
    )

    discursivas_lote, _ = _gerar_estruturado(
        f"""
{base}

Produza exatamente 2 questões discursivas.
Cada uma deve apresentar um resumo clínico com 3 a 5 erros conceituais discretos para o aluno
identificar, explicar e corrigir. Não revele os erros no enunciado. Inclua espelho detalhado,
habilidade e referências. Não produza questões objetivas nesta resposta.
""",
        DiscursivasLoteSchema,
        4500,
    )

    distribuicoes = [
        (2, 2, 1),
        (2, 2, 1),
        (1, 3, 1),
    ]
    objetivas = []

    for numero_lote, (basicas, intermediarias, avancadas) in enumerate(
        distribuicoes,
        start=1,
    ):
        anteriores = "\n".join(
            f"- {questao.texto_base[:180]} | {questao.enunciado[:120]}"
            for questao in objetivas
        ) or "- Nenhuma questão anterior."
        lote, _ = _gerar_estruturado(
            f"""
{base}

{DIRETRIZES_ENAMED_OBJETIVAS}

Produza o lote {numero_lote} de 3, contendo exatamente 5 questões objetivas inéditas de resposta única.
Distribuição obrigatória neste lote: {basicas} básicas, {intermediarias} intermediárias e {avancadas} avançada(s).

Requisitos adicionais do lote:
- preencha `texto_base` e `enunciado` separadamente;
- em `nivel_cognitivo`, use exatamente: lembrar, compreender, aplicar, analisar ou avaliar;
- em `alinhamento_enamed`, resuma área principal/secundária pertinente, perfil do avaliado,
  competência e domínio de conteúdo mobilizados;
- em `justificativa`, apresente cinco blocos em linhas separadas, no formato:
  A — CERTA/ERRADA: explicação; B — CERTA/ERRADA: explicação; e assim até E;
- não use perguntas de mera identificação de espécie quando o mesmo conteúdo puder avaliar
  integração entre dados clínicos, morfofisiologia, patogênese, evidência diagnóstica e mecanismo;
- o texto-base precisa conter os dados necessários, mas não dados ornamentais.

Não repita nem parafraseie excessivamente estes itens já gerados:
{anteriores}

Não produza slides nem questões discursivas nesta resposta.
""",
            ObjetivasLoteSchema,
            8000,
        )
        objetivas.extend(lote.objetivas)

    return PacoteEstudoSchema(
        slides=slides_lote.slides,
        objetivas=objetivas,
        discursivas=discursivas_lote.discursivas,
    )


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
    tools = [{"url_context": {}}] if urls else []
    if tema.permitir_fontes_externas and getattr(settings, "GEMINI_ENABLE_SEARCH", True):
        tools.append({"google_search": {}})
    resposta, raw = _gerar_estruturado(
        prompt,
        RespostaTutorSchema,
        4000,
        tools=tools or None,
    )
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
