from django.test import SimpleTestCase

from core.services.question_generation import _muito_semelhante


class QuestaoIneditaTest(SimpleTestCase):
    def test_detecta_mesma_vinheta_com_alteracao_superficial(self):
        original = (
            "Paciente de 24 anos apresenta febre, odinofagia e linfonodomegalia cervical após cinco dias. "
            "O hemograma mostra linfocitose e a avaliação clínica sugere infecção viral. "
            "Considerando os dados, assinale o mecanismo imunológico predominante."
        )
        parafrase_superficial = (
            "Paciente de 25 anos apresenta febre, odinofagia e linfonodomegalia cervical após seis dias. "
            "O hemograma demonstra linfocitose e a avaliação clínica sugere infecção viral. "
            "Considerando os dados, assinale o mecanismo imunológico predominante."
        )
        self.assertTrue(_muito_semelhante(original, parafrase_superficial))

    def test_permite_mesmo_conteudo_em_cenario_realmente_diferente(self):
        questao_a = (
            "Paciente com pneumonia bacteriana apresenta neutrofilia e consolidação pulmonar. "
            "A questão solicita relacionar quimiotaxia, fagocitose e eliminação bacteriana."
        )
        questao_b = (
            "Após vacinação, um estudante acompanha a resposta secundária meses depois da dose inicial. "
            "A questão solicita interpretar expansão clonal, células de memória e produção de anticorpos."
        )
        self.assertFalse(_muito_semelhante(questao_a, questao_b))
