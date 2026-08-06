import json

from django.test import SimpleTestCase

from core.services.gemini import AlternativasSchema, PacoteEstudoSchema, QuestaoObjetivaSchema


class GeminiSchemaCompatibilidadeTest(SimpleTestCase):
    def test_schema_nao_usa_additional_properties(self):
        schema_texto = json.dumps(PacoteEstudoSchema.model_json_schema())
        self.assertNotIn("additionalProperties", schema_texto)

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
