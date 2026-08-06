from django.test import TestCase
from django.urls import reverse
from core.models import Tema, Turma, Usuario


class CadastroTest(TestCase):
    def setUp(self):
        self.turma = Turma.objects.create(codigo="A", semestre="2026/2")

    def test_primeiro_acesso_cria_usuario_por_rgm(self):
        response = self.client.post(reverse("primeiro_acesso"), {
            "rgm": "123456",
            "nome": "Aluno Teste",
            "turma": self.turma.pk,
            "password1": "SenhaForte2026!",
            "password2": "SenhaForte2026!",
        })
        self.assertEqual(response.status_code, 302)
        user = Usuario.objects.get(rgm="123456")
        self.assertEqual(user.username, "123456")
        self.assertEqual(user.turma, self.turma)
        self.assertTrue(user.check_password("SenhaForte2026!"))


class AcessoTest(TestCase):
    def setUp(self):
        turma = Turma.objects.create(codigo="A", semestre="2026/2")
        self.aluno = Usuario.objects.create_user(
            username="999", rgm="999", password="SenhaForte2026!",
            papel=Usuario.Papel.ALUNO, turma=turma
        )
        self.tema = Tema.objects.create(titulo="Imunologia clínica", pacote_publicado=False)

    def test_aluno_ve_dashboard(self):
        self.client.login(username="999", password="SenhaForte2026!")
        response = self.client.get(reverse("aluno_dashboard"))
        self.assertEqual(response.status_code, 200)
