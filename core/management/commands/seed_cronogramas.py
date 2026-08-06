from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Aula, FonteConhecimento, Tema, Turma


TEMAS = [
    ("Apresentação do componente e resgate de conteúdo", True),
    ("Análise de casos clínicos — Bactérias 1", True),
    ("Análise de casos clínicos — Bactérias 2", True),
    ("Evidência diagnóstica — Coloração de Gram", True),
    ("Interpretação de antibiogramas", True),
    ("Análise de casos clínicos de virologia médica", True),
    ("Análise de casos clínicos de micologia médica", True),
    ("Parasitoses de interesse clínico", True),
    ("Imunologia clínica", True),
    ("Imunopatologias: autoimunidade, imunodeficiências e hipersensibilidades", True),
    ("Análise de casos clínicos em imunopatologias", True),
    ("Oncobiologia e imunoterapia", True),
    ("Estudo de casos clínicos em oncobiologia", True),
    ("Evidência diagnóstica — Microscopia de parasitos", True),
]

PADRAO_ATIVA = "Metodologia ativa: uso de TICs e IA na resolução de casos clínicos"
PADRAO_EXPOSITIVA = "Metodologia ativa: aula expositiva dialogada"
RECURSOS_TIC = "Datashow, computador e dispositivos eletrônicos pessoais"
RECURSOS_SALA = "Datashow, computador e quadro"


def d(dia, mes):
    return date(2026, mes, dia)


def linha(data, conteudo, tema=None, ch="3h/P", atividade=PADRAO_ATIVA, recursos=RECURSOS_TIC,
          grupos="TODOS", local="SALA DE AULA", categoria="CONTEUDO", estudo=True, horario="15h30-18h"):
    return {
        "data": data, "horario": horario, "conteudo": conteudo, "tema": tema,
        "carga_horaria": ch, "atividade": atividade, "recursos": recursos,
        "grupos": grupos, "local": local, "categoria": categoria,
        "disponivel_para_estudo": estudo,
    }


CRONOGRAMAS = {
    "A": [
        linha(d(3,8), "Apresentação do componente. Resgate de conteúdo", TEMAS[0][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(10,8), "Análise de casos clínicos - Bactérias 1", TEMAS[1][0]),
        linha(d(17,8), "Análise de casos clínicos - Bactérias 2", TEMAS[2][0]),
        linha(d(24,8), "Evidência diagnóstica - Coloração de Gram", TEMAS[3][0], atividade="Confecção e coloração de lâminas pelo método de Gram", recursos="Lâminas, microscópios, kit de coloração e meios com bactérias", grupos="Grupos 1 e 2: laboratório; grupos 3 e 4: atividade formativa no Blackboard", local="LAB - BLOCO G"),
        linha(d(31,8), "Evidência diagnóstica - Coloração de Gram", TEMAS[3][0], atividade="Confecção e coloração de lâminas pelo método de Gram", recursos="Lâminas, microscópios, kit de coloração e meios com bactérias", grupos="Grupos 3 e 4: laboratório; grupos 1 e 2: atividade formativa no Blackboard", local="LAB - BLOCO G"),
        linha(d(7,9), "Feriado - Independência do Brasil", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(14,9), "Interpretação de Antibiogramas", TEMAS[4][0]),
        linha(d(21,9), "Análise de casos clínicos de virologia médica", TEMAS[5][0]),
        linha(d(28,9), "1ª avaliação de aprendizagem - Feedback", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Datashow, computador, dispositivos eletrônicos pessoais e espelho de prova"),
        linha(d(5,10), "Análise de casos clínicos de micologia médica", TEMAS[6][0]),
        linha(d(12,10), "Feriado - Nossa Senhora de Aparecida", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(19,10), "Parasitoses de interesse clínico", TEMAS[7][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(26,10), "Imunologia clínica", TEMAS[8][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(2,11), "Feriado - Dia dos Finados", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(9,11), "Imunopatologias: Autoimunidade, Imunodeficiências e hipersensibilidades", TEMAS[9][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(16,11), "Análise de casos clínicos em imunopatologias", TEMAS[10][0]),
        linha(d(23,11), "Tempo de estudo e finalização das atividades formativas", categoria="ORGANIZACAO", estudo=False, ch="3h/T", atividade=PADRAO_EXPOSITIVA, recursos=RECURSOS_SALA),
        linha(d(28,11), "Prova Integrada", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos", horario="08h-12h"),
        linha(d(30,11), "Reposição das avaliações de aprendizagem", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos"),
        linha(d(7,12), "Recesso", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(14,12), "Avaliação Final", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos"),
        linha(None, "Oncobiologia e imunoterapia — reposição a ajustar com a turma", TEMAS[11][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(None, "Estudo de casos clínicos em oncobiologia — reposição a ajustar com a turma", TEMAS[12][0]),
        linha(None, "Evidência diagnóstica - Microscopia de parasitos — reposição a ajustar com a turma", TEMAS[13][0], atividade="Identificação das formas evolutivas de parasitos", recursos="Lâminas e microscópios", local="LAB - BLOCO G"),
    ],
    "B": [
        linha(d(4,8), "Apresentação do componente. Resgate de conteúdo", TEMAS[0][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(11,8), "Análise de casos clínicos - Bactérias 1", TEMAS[1][0]),
        linha(d(18,8), "Análise de casos clínicos - Bactérias 2", TEMAS[2][0]),
        linha(d(25,8), "Evidência diagnóstica - Coloração de Gram", TEMAS[3][0], atividade="Confecção e coloração de lâminas pelo método de Gram", recursos="Lâminas, microscópios, kit de coloração e meios com bactérias", grupos="Grupos 1 e 2: laboratório; grupos 3 e 4: atividade formativa no Blackboard", local="LABORATÓRIO - BLOCO G"),
        linha(d(1,9), "Evidência diagnóstica - Coloração de Gram", TEMAS[3][0], atividade="Confecção e coloração de lâminas pelo método de Gram", recursos="Lâminas, microscópios, kit de coloração e meios com bactérias", grupos="Grupos 3 e 4: laboratório; grupos 1 e 2: atividade formativa no Blackboard", local="LABORATÓRIO - BLOCO G"),
        linha(d(8,9), "Interpretação de Antibiogramas", TEMAS[4][0]),
        linha(d(15,9), "Análise de casos clínicos de virologia médica", TEMAS[5][0]),
        linha(d(22,9), "1ª avaliação de aprendizagem - Feedback", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Datashow, computador, dispositivos eletrônicos pessoais e espelho de prova"),
        linha(d(29,9), "Análise de casos clínicos de micologia médica", TEMAS[6][0]),
        linha(d(6,10), "Feira das profissões (sem atividades acadêmicas regulares)", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(13,10), "Parasitoses de interesse clínico", TEMAS[7][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(20,10), "Imunologia clínica", TEMAS[8][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(27,10), "Imunopatologias: Autoimunidade, Imunodeficiências e hipersensibilidades", TEMAS[9][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(3,11), "Análise de casos clínicos em imunopatologias", TEMAS[10][0]),
        linha(d(10,11), "Oncobiologia e imunoterapia", TEMAS[11][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(17,11), "Estudo de casos clínicos em oncobiologia", TEMAS[12][0]),
        linha(d(24,11), "Tempo de estudo e finalização das atividades formativas", categoria="ORGANIZACAO", estudo=False, ch="3h/T", atividade=PADRAO_EXPOSITIVA, recursos=RECURSOS_SALA),
        linha(d(28,11), "Prova Integrada", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos", horario="08h-12h"),
        linha(d(1,12), "Reposição das avaliações de aprendizagem", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos"),
        linha(d(8,12), "Feriado - Nossa Senhora da Conceição", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(15,12), "Avaliação Final", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos"),
        linha(None, "Evidência diagnóstica - Microscopia de parasitos — reposição a ajustar com a turma", TEMAS[13][0], atividade="Identificação das formas evolutivas de parasitos", recursos="Lâminas e microscópios", local="LABORATÓRIO - BLOCO G"),
    ],
    "C": [
        linha(d(6,8), "Apresentação do componente. Resgate de conteúdo", TEMAS[0][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(13,8), "Análise de casos clínicos - Bactérias 1", TEMAS[1][0]),
        linha(d(20,8), "Análise de casos clínicos - Bactérias 2", TEMAS[2][0]),
        linha(d(27,8), "Evidência diagnóstica - Coloração de Gram", TEMAS[3][0], atividade="Confecção e coloração de lâminas pelo método de Gram", recursos="Lâminas, microscópios, kit de coloração e meios com bactérias", grupos="Grupos 1 e 2: laboratório; grupos 3 e 4: atividade formativa no Blackboard", local="LAB - BLOCO G"),
        linha(d(3,9), "Evidência diagnóstica - Coloração de Gram", TEMAS[3][0], atividade="Confecção e coloração de lâminas pelo método de Gram", recursos="Lâminas, microscópios, kit de coloração e meios com bactérias", grupos="Grupos 3 e 4: laboratório; grupos 1 e 2: atividade formativa no Blackboard", local="LAB - BLOCO G"),
        linha(d(10,9), "Interpretação de Antibiogramas", TEMAS[4][0]),
        linha(d(17,9), "Análise de casos clínicos de virologia médica", TEMAS[5][0]),
        linha(d(24,9), "1ª avaliação de aprendizagem - Feedback", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Datashow, computador, dispositivos eletrônicos pessoais e espelho de prova"),
        linha(d(1,10), "Análise de casos clínicos de micologia médica", TEMAS[6][0]),
        linha(d(8,10), "Semana de resgate de conhecimentos", categoria="ORGANIZACAO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(15,10), "Feriado - Dia do Professor", categoria="RECESSO", estudo=False, ch="", atividade="", recursos="", grupos="", local=""),
        linha(d(22,10), "Parasitoses de interesse clínico", TEMAS[7][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(29,10), "Imunologia clínica", TEMAS[8][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(5,11), "Imunopatologias: Autoimunidade, Imunodeficiências e hipersensibilidades", TEMAS[9][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(12,11), "Análise de casos clínicos em imunopatologias", TEMAS[10][0]),
        linha(d(19,11), "Oncobiologia e imunoterapia", TEMAS[11][0], "3h/T", PADRAO_EXPOSITIVA, RECURSOS_SALA),
        linha(d(26,11), "Tempo de estudo e finalização das atividades formativas", categoria="ORGANIZACAO", estudo=False, ch="3h/T", atividade=PADRAO_EXPOSITIVA, recursos=RECURSOS_SALA),
        linha(d(28,11), "Prova Integrada", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos", horario="08h-12h"),
        linha(d(3,12), "Reposição das avaliações de aprendizagem", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos"),
        linha(d(10,12), "Avaliação Final", categoria="AVALIACAO", estudo=False, ch="3h/T", atividade="Avaliação presencial", recursos="Provas e espelhos"),
        linha(None, "Evidência diagnóstica - Microscopia de parasitos — reposição a ajustar com a turma", TEMAS[13][0], atividade="Identificação das formas evolutivas de parasitos", recursos="Lâminas e microscópios", local="LAB - BLOCO G"),
        linha(None, "Estudo de casos clínicos em oncobiologia — reposição a ajustar com a turma", TEMAS[12][0]),
    ],
}


class Command(BaseCommand):
    help = "Cria turmas, temas, fonte principal e cronogramas MAPD-2 2026/2."

    @transaction.atomic
    def handle(self, *args, **options):
        tema_map = {}
        for ordem, (titulo, ativo) in enumerate(TEMAS, start=1):
            tema, _ = Tema.objects.update_or_create(
                titulo=titulo,
                defaults={
                    "ordem": ordem,
                    "ativo": ativo,
                    "descricao": f"Revisão, prática e tutoria sobre {titulo}.",
                },
            )
            tema_map[titulo] = tema

        FonteConhecimento.objects.get_or_create(
            url="https://mecanismos-medicos-rn-2026.rodrigoniskier.chatgpt.site/",
            defaults={
                "titulo": "Mecanismos de Agressão, Patológicos e de Defesa — página principal",
                "principal": True,
                "aprovada": True,
                "resumo_auditoria": "Fonte autoral principal indicada pelo professor.",
                "conteudo": (
                    "Material autoral de Patologia Médica, Introdução à Microbiologia Médica, "
                    "Microbiologia Clínica e Imunologia Clínica. Estrutura de estudo voltada a "
                    "raciocínio mecanístico, interpretação de evidências e decisões clínicas."
                ),
            },
        )

        FonteConhecimento.objects.get_or_create(
            titulo="Manual de Avaliação de Aprendizagem — Medicina UNIPÊ 2025",
            url="",
            defaults={
                "principal": False,
                "aprovada": True,
                "resumo_auditoria": "Síntese operacional do manual institucional fornecido pelo professor.",
                "conteudo": (
                    "As avaliações escritas podem utilizar questões dissertativas e testes de múltipla escolha, "
                    "desde que sejam contextualizados e compatíveis com os processos de aprendizagem. "
                    "A avaliação formativa é contínua e tem como finalidade fornecer feedback construtivo ao aluno. "
                    "O processo deve preservar equidade, coerência dos critérios de pontuação e revisão docente."
                ),
            },
        )

        total = 0
        for codigo, linhas in CRONOGRAMAS.items():
            turma, _ = Turma.objects.update_or_create(
                codigo=codigo, semestre="2026/2",
                defaults={"periodo": "4º", "ativa": True},
            )
            Aula.objects.filter(turma=turma).delete()
            for dados_originais in linhas:
                dados = dados_originais.copy()
                tema_titulo = dados.pop("tema", None)
                Aula.objects.create(
                    turma=turma,
                    tema=tema_map.get(tema_titulo),
                    docente="Rodrigo Niskier",
                    **dados,
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed concluído: 3 turmas, {len(TEMAS)} temas e {total} entradas de cronograma."
        ))
