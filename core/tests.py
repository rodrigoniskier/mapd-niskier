from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Aula,
    Questao,
    RevisaoProgresso,
    SlideRevisao,
    Tema,
    Tentativa,
    Turma,
    Usuario,
)


class BaseMAPDTest(TestCase):
    def setUp(self):
        self.turma_a = Turma.objects.create(codigo="A", semestre="2026/2")
        self.turma_b = Turma.objects.create(codigo="B", semestre="2026/2")
        self.tema = Tema.objects.create(titulo="Imunologia clínica", pacote_publicado=True)
        Aula.objects.create(
            turma=self.turma_a,
            tema=self.tema,
            conteudo="Imunologia clínica",
            data=timezone.localdate(),
            disponivel_para_estudo=True,
        )
        for ordem in range(1, 4):
            SlideRevisao.objects.create(
                tema=self.tema,
                ordem=ordem,
                titulo=f"Slide {ordem}",
                conteudo="Conteúdo mecanístico de revisão suficientemente detalhado.",
                pontos_chave=["Ponto 1", "Ponto 2"],
                aprovado=True,
            )
        for n in range(15):
            Questao.objects.create(
                tema=self.tema,
                tipo=Questao.Tipo.OBJETIVA,
                enunciado=f"Caso clínico contextualizado número {n} com dados suficientes para raciocínio.",
                alternativas={"A": "Alternativa A", "B": "Alternativa B", "C": "Alternativa C", "D": "Alternativa D", "E": "Alternativa E"},
                gabarito="A",
                justificativa="Justificativa mecanística do gabarito e análise do caso.",
                dificuldade=["básica", "intermediária", "avançada"][n % 3],
                status=Questao.Status.APROVADA,
            )
        for n in range(2):
            Questao.objects.create(
                tema=self.tema,
                tipo=Questao.Tipo.DISCURSIVA,
                enunciado=f"Resumo clínico {n} contendo erros conceituais discretos para análise.",
                erros_propositais=["Erro 1", "Erro 2", "Erro 3"],
                justificativa="Espelho detalhado para correção da resposta discursiva.",
                status=Questao.Status.APROVADA,
            )


class CadastroTest(BaseMAPDTest):
    def test_primeiro_acesso_vincula_rgm_e_turma(self):
        response = self.client.post(
            reverse("primeiro_acesso"),
            {
                "rgm": "123456",
                "nome": "Aluno Teste Completo",
                "turma": self.turma_a.pk,
                "codigo_turma": "",
                "password1": "SenhaForte2026!",
                "password2": "SenhaForte2026!",
                "aceite": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = Usuario.objects.get(rgm="123456")
        self.assertEqual(user.username, "123456")
        self.assertEqual(user.turma, self.turma_a)
        self.assertTrue(user.check_password("SenhaForte2026!"))
        self.assertIsNotNone(user.aceite_termos_em)

    def test_codigo_turma_e_exigido_quando_configurado(self):
        self.turma_a.codigo_ingresso = "MAPD-A"
        self.turma_a.save()
        response = self.client.post(
            reverse("primeiro_acesso"),
            {
                "rgm": "123457",
                "nome": "Aluno Teste",
                "turma": self.turma_a.pk,
                "codigo_turma": "ERRADO",
                "password1": "SenhaForte2026!",
                "password2": "SenhaForte2026!",
                "aceite": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Usuario.objects.filter(rgm="123457").exists())


class FluxoAlunoTest(BaseMAPDTest):
    def setUp(self):
        super().setUp()
        self.aluno = Usuario.objects.create_user(
            username="999",
            rgm="999",
            password="SenhaForte2026!",
            papel=Usuario.Papel.ALUNO,
            turma=self.turma_a,
        )
        self.client.login(username="999", password="SenhaForte2026!")

    def test_aluno_nao_acessa_tema_de_outra_turma(self):
        outro = Tema.objects.create(titulo="Tema exclusivo B", pacote_publicado=True)
        Aula.objects.create(turma=self.turma_b, tema=outro, conteudo="Outro")
        response = self.client.get(reverse("escolher_modo", args=[outro.slug]))
        self.assertEqual(response.status_code, 404)

    def test_tentativa_tem_nove_objetivas_e_uma_discursiva(self):
        RevisaoProgresso.objects.create(aluno=self.aluno, tema=self.tema, concluida_em=timezone.now())
        response = self.client.post(reverse("iniciar_avaliacao", args=[self.tema.slug]))
        self.assertEqual(response.status_code, 302)
        tentativa = Tentativa.objects.get(aluno=self.aluno, tema=self.tema)
        self.assertEqual(tentativa.itens.count(), 10)
        self.assertEqual(tentativa.itens.filter(questao__tipo=Questao.Tipo.OBJETIVA).count(), 9)
        self.assertEqual(tentativa.itens.filter(questao__tipo=Questao.Tipo.DISCURSIVA).count(), 1)

    @override_settings(GEMINI_API_KEY="")
    def test_finalizacao_funciona_sem_api(self):
        RevisaoProgresso.objects.create(aluno=self.aluno, tema=self.tema, concluida_em=timezone.now())
        self.client.post(reverse("iniciar_avaliacao", args=[self.tema.slug]))
        tentativa = Tentativa.objects.get(aluno=self.aluno, tema=self.tema)
        dados = {}
        for item in tentativa.itens.select_related("questao"):
            dados[f"q_{item.questao_id}"] = "A" if item.questao.tipo == Questao.Tipo.OBJETIVA else "Identifico e corrijo os três erros."
        response = self.client.post(reverse("finalizar_avaliacao", args=[tentativa.pk]), dados)
        self.assertEqual(response.status_code, 302)
        tentativa.refresh_from_db()
        self.assertEqual(tentativa.nota_objetiva, Decimal("7.20"))
        self.assertTrue(tentativa.feedback)
        self.assertEqual(tentativa.status, Tentativa.Status.REVISAO)


class ProfessorTest(BaseMAPDTest):
    def setUp(self):
        super().setUp()
        self.professor = Usuario.objects.create_superuser(
            username="rodrigo", email="prof@example.com", password="SenhaForte2026!"
        )
        self.professor.papel = Usuario.Papel.PROFESSOR
        self.professor.save()
        self.client.login(username="rodrigo", password="SenhaForte2026!")

    def test_dashboard_professor(self):
        response = self.client.get(reverse("professor_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestão acadêmica MAPD")

    def test_edicao_de_tema(self):
        response = self.client.post(
            reverse("tema_editar", args=[self.tema.pk]),
            {
                "titulo": "Imunologia clínica atualizada",
                "descricao": "Descrição",
                "ordem": 1,
                "ativo": "on",
                "visivel_alunos": "on",
                "tentativas_permitidas": 3,
                "nota_minima": "6.00",
                "permitir_fontes_externas": "on",
                "referencia_principal": self.tema.referencia_principal,
                "instrucoes_ia": "",
                "liberar_em": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.tema.refresh_from_db()
        self.assertEqual(self.tema.titulo, "Imunologia clínica atualizada")
