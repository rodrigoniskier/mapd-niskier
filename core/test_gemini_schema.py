from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from pydantic import BaseModel

from core.services import gemini
from core.services.gemini import AlternativasSchema, PacoteEstudoSchema, QuestaoObjetivaSchema


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
        questao = QuestaoObjetivaSchema(
            enunciado="Caso clínico suficientemente detalhado para avaliar o raciocínio mecanístico do estudante de Medicina." * 2,
            alternativas=AlternativasSchema(
                A="Alternativa A",
                B="Alternativa B",
                C="Alternativa C",
                D="Alternativa D",
                E="Alternativa E",
            ),
            gabarito="A",
            justificativa="Justificativa mecanística suficientemente detalhada para validar o gabarito e os distratores.",
            dificuldade="intermediária",
            nivel_cognitivo="aplicação",
            habilidade="Integrar mecanismo e manifestação clínica.",
            referencias=[],
        )
        self.assertEqual(
            questao.alternativas_dict(),
            {
                "A": "Alternativa A",
                "B": "Alternativa B",
                "C": "Alternativa C",
                "D": "Alternativa D",
                "E": "Alternativa E",
            },
        )

    def test_remove_cerca_markdown_de_json(self):
        texto = '```json\n{"valor":"ok"}\n```'
        self.assertEqual(gemini._limpar_json_resposta(texto), '{"valor":"ok"}')

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
