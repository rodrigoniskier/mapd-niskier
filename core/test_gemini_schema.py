from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from pydantic import BaseModel, ValidationError

from core.services import gemini
from core.services.gemini import (
    AlternativasSchema,
    DIRETRIZES_ENAMED_OBJETIVAS,
    DiscursivasLoteSchema,
    ObjetivasLoteSchema,
    PacoteEstudoSchema,
    QuestaoObjetivaSchema,
    SlidesLoteSchema,
)


def encontrar_chave(objeto, chave_proibida):
    """Percorre o schema e procura a chave real, ignorando textos descritivos."""
    if isinstance(objeto, dict):
        if chave_proibida in objeto:
            return True
        return any(encontrar_chave(valor, chave_proibida) for valor in objeto.values())
    if isinstance(objeto, list):
        return any(encontrar_chave(valor, chave_proibida) for valor in objeto)
    return False


class SaidaMinima(BaseModel):
    valor: str


class ClienteFalso:
    def __init__(self):
        self.closed = False
        self.models = self.Modelos(self)

    class Modelos:
        def __init__(self, cliente):
            self.cliente = cliente

        def generate_content(self, **kwargs):
            if self.cliente.closed:
                raise RuntimeError("cliente fechado antes da requisição")
            return SimpleNamespace(text='{"valor":"ok"}')

    def close(self):
        self.closed = True


def questao_valida(**alteracoes):
    dados = {
        "texto_base": (
            "Um adulto apresenta quadro infeccioso com dados clínicos, laboratoriais e "
            "microbiológicos suficientes para relacionar o mecanismo bacteriano à manifestação observada."
        ),
        "enunciado": "Considerando o caso apresentado, assinale a alternativa que melhor explica o mecanismo envolvido.",
        "alternativas": AlternativasSchema(
            A="Ativação de um mecanismo bacteriano compatível com os dados do caso.",
            B="Inibição de uma via que não explica os achados apresentados.",
            C="Produção de um fator sem relação causal com o quadro descrito.",
            D="Alteração estrutural incompatível com a evidência laboratorial.",
            E="Resposta do hospedeiro que não corresponde ao mecanismo solicitado.",
        ),
        "gabarito": "A",
        "justificativa": (
            "A — CERTA: relaciona corretamente os dados clínicos ao mecanismo bacteriano descrito.\n"
            "B — ERRADA: propõe uma via incompatível com os achados apresentados.\n"
            "C — ERRADA: atribui causalidade a um fator que não explica o caso.\n"
            "D — ERRADA: contradiz a evidência laboratorial disponível.\n"
            "E — ERRADA: descreve fenômeno distinto da tarefa solicitada no enunciado."
        ),
        "dificuldade": "intermediária",
        "nivel_cognitivo": "analisar",
        "habilidade": "Integrar dados clínicos e microbiológicos para explicar um mecanismo de doença.",
        "alinhamento_enamed": (
            "Área de bases biológicas, competência de raciocínio clínico e domínio dos processos celulares alterados."
        ),
        "referencias": [],
    }
    dados.update(alteracoes)
    return QuestaoObjetivaSchema(**dados)


class GeminiSchemaCompatibilidadeTest(SimpleTestCase):
    def test_schema_nao_usa_chave_additional_properties(self):
        schema = PacoteEstudoSchema.model_json_schema()
        self.assertFalse(encontrar_chave(schema, "additionalProperties"))

    def test_configuracao_nao_envia_response_schema(self):
        config = gemini._config_estruturada(100)
        dados = config.model_dump(exclude_none=True)
        self.assertNotIn("response_schema", dados)
        self.assertNotIn("response_json_schema", dados)
        self.assertEqual(dados.get("response_mime_type"), "application/json")

    def test_alternativas_sao_convertidas_para_json_simples(self):
        questao = questao_valida()
        self.assertEqual(set(questao.alternativas_dict()), {"A", "B", "C", "D", "E"})
        self.assertIn(questao.texto_base, questao.enunciado_completo())
        self.assertIn(questao.enunciado, questao.enunciado_completo())
        self.assertEqual(questao.referencias_registro()[-1]["titulo"], "Alinhamento ENAMED/DCNs")

    def test_rejeita_alternativas_repetidas(self):
        with self.assertRaises(ValidationError):
            AlternativasSchema(A="Igual", B="Igual", C="C", D="D", E="E")

    def test_rejeita_comando_negativo(self):
        with self.assertRaises(ValidationError):
            questao_valida(enunciado="Considerando o caso, assinale a alternativa que não explica o mecanismo.")

    def test_exige_justificativa_de_cada_alternativa(self):
        with self.assertRaises(ValidationError):
            questao_valida(justificativa="A — CERTA: correta. B — ERRADA: incorreta.")

    def test_diretrizes_enamed_contem_componentes_do_projeto(self):
        for termo in (
            "TEXTO-BASE",
            "ENUNCIADO/COMANDO",
            "Distratores",
            "paralelismo sintático",
            "Taxonomia de Bloom",
            "CERTA",
            "ERRADA",
        ):
            self.assertIn(termo.casefold(), DIRETRIZES_ENAMED_OBJETIVAS.casefold())

    def test_remove_cerca_markdown_de_json(self):
        texto = '```json\n{"valor":"ok"}\n```'
        self.assertEqual(gemini._limpar_json_resposta(texto), '{"valor":"ok"}')

    def test_repara_virgula_final_simples(self):
        resultado = gemini._validar_json_resposta('{"valor":"ok",}', SaidaMinima)
        self.assertEqual(resultado.valor, "ok")

    def test_lotes_limitam_tamanho_da_resposta(self):
        self.assertIn("slides", SlidesLoteSchema.model_fields)
        self.assertIn("objetivas", ObjetivasLoteSchema.model_fields)
        self.assertIn("discursivas", DiscursivasLoteSchema.model_fields)

    @override_settings(GEMINI_MODEL="modelo-teste", GEMINI_FALLBACK_MODEL="")
    @patch("core.services.gemini._config_estruturada", return_value={})
    @patch("core.services.gemini._client")
    def test_cliente_permanece_aberto_ate_terminar_a_requisicao(
        self,
        client_mock,
        config_mock,
    ):
        cliente = ClienteFalso()
        client_mock.return_value = cliente

        resultado, _ = gemini._gerar_estruturado(
            "prompt",
            SaidaMinima,
            100,
        )

        self.assertEqual(resultado.valor, "ok")
        self.assertTrue(cliente.closed)
        client_mock.assert_called_once()
        config_mock.assert_called_once()
