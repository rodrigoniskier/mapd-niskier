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
