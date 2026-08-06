from .models import ConfiguracaoPlataforma


def plataforma(request):
    try:
        return {"configuracao_plataforma": ConfiguracaoPlataforma.atual()}
    except Exception:
        return {"configuracao_plataforma": None}
