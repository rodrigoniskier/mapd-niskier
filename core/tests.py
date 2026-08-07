from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import (
    Aula,
    Questao,
    RevisaoProgresso,
    SessaoChat,
    SlideRevisao,
    Tema,
    Tentativa,
    Turma,
    Usuario,
)


class FakeObjetiva:
    def __init__(self, numero):
        self.numero = numero
        self.gabarito = "A"
        self.justificativa = (
            "A — CERTA: justificativa correta.\n"
            "B — ERRADA: distrator plausível.\n"
            "C — ERRADA: distrator plausível.\n"
            "D — ERRADA: distrator plausível.\n"
            "E — ERRADA: distrator plausível."
        )
        self.dificuldade = "intermediária"
        self.nivel_cognitivo = "aplicar"
        self.habilidade = f"Integrar mecanismo e raciocínio clínico no cenário {numero}."

    def enunciado_completo(self):
        return f"Novo caso clínico adicional {self.numero} com contexto e decisão própria.\n\nAssinale a melhor interpretação."

    def alternativas_dict(self):
        return {
            "A": f"Alternativa correta {self.numero}",
            "B": f"Distrator B {self.numero}",
            "C": f"Distrator C {self.numero}",
            "D": f"Distrator D {self.numero}",
            "E": f"Distrator E {self.numero}",
        }

    def referencias_registro(self):
        return []


class FakeDiscursiva:
    def __init__(self, numero):
        self.enunciado = f"Nova questão discursiva adicional {numero} com cenário clínico inédito."
        self.erros_propositais = ["Erro 1", "Erro 2", "Erro 3"]
        self.justificativa = "Espelho detalhado de correção da questão discursiva adicional."
        self.habilidade = "Analisar criticamente mecanismos e corrigir erros conceituais."
        self.referencias = []


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

    def test_concluir_revisao_marca_progresso_e_avanca(self):
        response = self.client.post(reverse("concluir_revisao", args=[self.tema.slug]))
        self.assertEqual(response.status_code, 302)
        progresso = RevisaoProgresso.objects.get(aluno=self.aluno, tema=self.tema)
        self.assertIsNotNone(progresso.concluida_em)
        self.assertEqual(progresso.slide_atual, 3)
        self.assertEqual(response.url, reverse("pre_avaliacao", args=[self.tema.slug]))

    def test_trilha_segue_ordem_cronologica_do_cronograma(self):
        tema_anterior = Tema.objects.create(titulo="Tema anterior", pacote_publicado=True)
        Aula.objects.create(
            turma=self.turma_a,
            tema=tema_anterior,
            conteudo="Conteúdo anterior",
            data=timezone.localdate() - timedelta(days=7),
        )
        tema_sem_data = Tema.objects.create(titulo="Tema sem data", pacote_publicado=True)
        Aula.objects.create(
            turma=self.turma_a,
            tema=tema_sem_data,
            conteudo="Conteúdo sem data",
            data=None,
        )
        response = self.client.get(reverse("aluno_dashboard"))
        ordem = [item["tema"].pk for item in response.context["temas"]]
        self.assertEqual(ordem[0], tema_anterior.pk)
        self.assertEqual(ordem[-1], tema_sem_data.pk)

    @patch("core.views.chat.responder_tutor")
    def test_plantao_aceita_conversa_continua_sem_limite_de_30_mensagens(self, responder_mock):
        responder_mock.return_value = SimpleNamespace(
            resposta="Resposta de teste da IA Niskier.",
            fontes=[],
            nivel_pista=0,
        )
        self.client.get(reverse("plantao", args=[self.tema.slug]))
        sessao = SessaoChat.objects.get(
            aluno=self.aluno,
            tema=self.tema,
            tentativa=None,
        )
        for numero in range(35):
            response = self.client.post(
                reverse("chat_enviar", args=[sessao.pk]),
                {"mensagem": f"Dúvida acadêmica número {numero}"},
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(sessao.mensagens.count(), 70)

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

    @override_settings(GEMINI_API_KEY="")
    def test_feedback_e_reconstruido_se_estiver_vazio(self):
        RevisaoProgresso.objects.create(aluno=self.aluno, tema=self.tema, concluida_em=timezone.now())
        self.client.post(reverse("iniciar_avaliacao", args=[self.tema.slug]))
        tentativa = Tentativa.objects.get(aluno=self.aluno, tema=self.tema)
        tentativa.feedback = ""
        tentativa.save(update_fields=["feedback"])
        response = self.client.get(reverse("feedback", args=[tentativa.pk]))
        self.assertEqual(response.status_code, 200)
        tentativa.refresh_from_db()
        self.assertTrue(tentativa.feedback)


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

    @patch("core.views.content.gerar_questoes_adicionais")
    def test_gerar_mais_questoes_preserva_banco_e_acrescenta_17(self, gerar_mock):
        gerar_mock.return_value = SimpleNamespace(
            objetivas=[FakeObjetiva(i) for i in range(15)],
            discursivas=[FakeDiscursiva(i) for i in range(2)],
        )
        total_antes = self.tema.questoes.count()
        response = self.client.post(reverse("gerar_mais_questoes", args=[self.tema.pk]))
        self.assertEqual(response.status_code, 302)
        self.tema.refresh_from_db()
        self.assertEqual(self.tema.questoes.count(), total_antes + 17)
        self.assertEqual(self.tema.questoes.filter(tipo=Questao.Tipo.OBJETIVA).count(), 30)
        self.assertEqual(self.tema.questoes.filter(tipo=Questao.Tipo.DISCURSIVA).count(), 4)
        self.assertTrue(self.tema.pacote_publicado)
