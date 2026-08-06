from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import ConfiguracaoPlataforma, FonteConhecimento, Usuario


class Command(BaseCommand):
    help = "Cria a configuração inicial, cadastra a fonte principal e ajusta perfis administrativos."

    def handle(self, *args, **options):
        config, created = ConfiguracaoPlataforma.objects.get_or_create(
            nome="MAPD Niskier",
            defaults={
                "subtitulo": "Mecanismos de Agressão, Patológicos e de Defesa",
                "instituicao": "Medicina — UNIPÊ",
            },
        )
        fonte, fonte_created = FonteConhecimento.objects.get_or_create(
            url="https://mecanismos-medicos-rn-2026.rodrigoniskier.chatgpt.site/",
            defaults={
                "titulo": "Mecanismos de Agressão, Patológicos e de Defesa — Prof. Rodrigo Niskier",
                "tipo": FonteConhecimento.Tipo.LIVRO,
                "principal": True,
                "aprovada": True,
                "permitir_contexto_url": True,
                "resumo_auditoria": "Fonte principal indicada pelo autor e professor responsável pela plataforma.",
                "auditada_em": timezone.now(),
            },
        )
        fonte.principal = True
        fonte.aprovada = True
        fonte.tipo = FonteConhecimento.Tipo.LIVRO
        fonte.permitir_contexto_url = True
        if not fonte.resumo_auditoria:
            fonte.resumo_auditoria = "Fonte principal indicada pelo autor e professor responsável pela plataforma."
        fonte.auditada_em = fonte.auditada_em or timezone.now()
        fonte.save(update_fields=["principal", "aprovada", "tipo", "permitir_contexto_url", "resumo_auditoria", "auditada_em", "atualizada_em"])

        ajustados = Usuario.objects.filter(is_superuser=True).update(papel=Usuario.Papel.PROFESSOR)
        self.stdout.write(
            self.style.SUCCESS(
                f"Plataforma preparada: configuração={'criada' if created else 'existente'}, "
                f"fonte={'criada' if fonte_created else 'existente'}, administradores ajustados={ajustados}."
            )
        )
