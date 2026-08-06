from django.test import SimpleTestCase

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


class GeminiSchemaCompatibilidadeTest(SimpleTestCase):
    def test_schema_nao_usa_chave_additional_properties(self):
        schema = PacoteEstudoSchema.model_json_schema()
        self.assertFalse(encontrar_chave(schema, "additionalProperties"))

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
