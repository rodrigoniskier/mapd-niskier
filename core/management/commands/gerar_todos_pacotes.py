from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Questao, SlideRevisao, TarefaIA, Tema
from core.services.gemini import gerar_pacote_estudo


class Command(BaseCommand):
    help = "Gera, como rascunho, os pacotes de todos os temas ativos usando a chave Gemini."

    def add_arguments(self, parser):
        parser.add_argument("--tema", type=int, help="ID de um tema específico")
        parser.add_argument("--substituir", action="store_true", help="Remove rascunhos anteriores gerados por IA")

    def handle(self, *args, **options):
        temas = Tema.objects.filter(ativo=True)
        if options.get("tema"):
            temas = temas.filter(pk=options["tema"])
        if not temas.exists():
            raise CommandError("Nenhum tema encontrado.")

        for tema in temas:
            tarefa = TarefaIA.objects.create(tipo=TarefaIA.Tipo.PACOTE, tema=tema)
            tarefa.status = TarefaIA.Status.PROCESSANDO
            tarefa.iniciada_em = timezone.now()
            tarefa.save(update_fields=["status", "iniciada_em"])
            self.stdout.write(f"Gerando: {tema.titulo}...")
            try:
                pacote = gerar_pacote_estudo(tema)
                with transaction.atomic():
                    if options.get("substituir"):
                        tema.slides.filter(aprovado=False).delete()
                        tema.questoes.filter(criada_por_ia=True, status=Questao.Status.RASCUNHO).delete()
                    for slide in pacote.slides[:3]:
                        SlideRevisao.objects.update_or_create(
                            tema=tema,
                            ordem=slide.ordem,
                            defaults={
                                "titulo": slide.titulo,
                                "conteudo": slide.conteudo,
                                "pontos_chave": slide.pontos_chave,
                                "aprovado": False,
                            },
                        )
                    for q in pacote.objetivas[:15]:
                        Questao.objects.create(
                            tema=tema,
                            tipo=Questao.Tipo.OBJETIVA,
                            enunciado=q.enunciado_completo(),
                            alternativas=q.alternativas_dict(),
                            gabarito=q.gabarito,
                            justificativa=q.justificativa,
                            dificuldade=q.dificuldade,
                            nivel_cognitivo=q.nivel_cognitivo,
                            habilidade=q.habilidade[:200],
                            referencias=q.referencias_registro(),
                            criada_por_ia=True,
                        )
                    for q in pacote.discursivas[:2]:
                        Questao.objects.create(
                            tema=tema,
                            tipo=Questao.Tipo.DISCURSIVA,
                            enunciado=q.enunciado,
                            erros_propositais=q.erros_propositais,
                            justificativa=q.justificativa,
                            habilidade=q.habilidade,
                            referencias=[f.model_dump() for f in q.referencias],
                            criada_por_ia=True,
                        )
                    tema.pacote_publicado = False
                    tema.save(update_fields=["pacote_publicado"])
                tarefa.status = TarefaIA.Status.CONCLUIDA
                tarefa.concluida_em = timezone.now()
                tarefa.save(update_fields=["status", "concluida_em"])
                self.stdout.write(self.style.SUCCESS(f"Concluído: {tema.titulo}"))
            except Exception as exc:
                tarefa.status = TarefaIA.Status.ERRO
                tarefa.mensagem_erro = str(exc)[:4000]
                tarefa.concluida_em = timezone.now()
                tarefa.save(update_fields=["status", "mensagem_erro", "concluida_em"])
                self.stderr.write(self.style.ERROR(f"Erro em {tema.titulo}: {exc}"))
