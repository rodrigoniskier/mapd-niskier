import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from core.models import FonteConhecimento


class Command(BaseCommand):
    help = "Importa o texto visível de uma URL como fonte de conhecimento."

    def add_arguments(self, parser):
        parser.add_argument("url")
        parser.add_argument("--titulo", default="Mecanismos de Agressão, Patológicos e de Defesa")
        parser.add_argument("--principal", action="store_true")

    def handle(self, *args, **options):
        url = options["url"]
        try:
            response = requests.get(url, timeout=30, headers={"User-Agent": "MAPD-Niskier/1.0"})
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Falha ao acessar a URL: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        texto = "\n".join(
            linha.strip() for linha in soup.get_text("\n").splitlines() if linha.strip()
        )
        texto = re.sub(r"\n{3,}", "\n\n", texto)
        if len(texto) < 300:
            raise CommandError("Pouco texto foi extraído. A página pode usar carregamento dinâmico.")

        fonte, created = FonteConhecimento.objects.update_or_create(
            url=url,
            defaults={
                "titulo": options["titulo"],
                "conteudo": texto,
                "principal": options["principal"],
                "aprovada": True,
                "resumo_auditoria": "Texto público importado automaticamente; revisão docente recomendada.",
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Criada' if created else 'Atualizada'}: {fonte.titulo} ({len(texto)} caracteres)"
        ))
