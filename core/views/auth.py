import csv
import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from ..decorators import aluno_required, professor_required
from ..forms import (
    AjusteNotaForm,
    AlunoForm,
    AulaForm,
    FonteConhecimentoForm,
    MensagemChatForm,
    PrimeiroAcessoForm,
    QuestaoForm,
    RGMAuthenticationForm,
    SlideRevisaoForm,
    TemaForm,
)
from ..models import (
    Aula,
    AuditoriaNota,
    ConfiguracaoPlataforma,
    FonteConhecimento,
    MensagemChat,
    Questao,
    QuestaoTentativa,
    RegistroAuditoria,
    Resposta,
    RevisaoProgresso,
    SessaoChat,
    SlideRevisao,
    TarefaIA,
    Tema,
    Tentativa,
    Turma,
    Usuario,
)
from ..services.gemini import (
    corrigir_discursiva,
    feedback_deterministico,
    gerar_feedback,
    gerar_pacote_estudo,
    responder_tutor,
)
from ..services.reports import certificado_pdf_response, qr_data_uri, relatorio_pdf_response
from ..services.selection import selecionar_questoes


class EntrarView(LoginView):
    template_name = "auth/login.html"
    authentication_form = RGMAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse("rotear_dashboard")


class SairView(LogoutView):
    next_page = reverse_lazy("login")


def primeiro_acesso(request):
    if request.user.is_authenticated:
        return redirect("rotear_dashboard")
    form = PrimeiroAcessoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        RegistroAuditoria.objects.create(
            usuario=user,
            acao="PRIMEIRO_ACESSO",
            objeto="Usuario",
            objeto_id=str(user.pk),
            detalhes={"turma": user.turma.codigo if user.turma else None, "rgm_hash": _hash_rgm(user.rgm)},
        )
        messages.success(request, "Cadastro concluído. Seu RGM foi vinculado à turma selecionada.")
        return redirect("aluno_dashboard")
    return render(
        request,
        "auth/primeiro_acesso.html",
        {"form": form, "configuracao": ConfiguracaoPlataforma.atual()},
    )


def _hash_rgm(rgm):
    return hashlib.sha256((rgm or "").encode("utf-8")).hexdigest()[:16]


@login_required
def rotear_dashboard(request):
    if request.user.e_professor:
        return redirect("professor_dashboard")
    return redirect("aluno_dashboard")
