import json

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Q
from django.utils import timezone

from .models import (
    Aula,
    FonteConhecimento,
    Questao,
    SlideRevisao,
    Tema,
    Turma,
    Usuario,
)


class StyledFormMixin:
    def _style_fields(self):
        for field in self.fields.values():
            css = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            field.widget.attrs.setdefault("class", css)


class PrimeiroAcessoForm(StyledFormMixin, UserCreationForm):
    rgm = forms.CharField(label="RGM", max_length=30)
    nome = forms.CharField(label="Nome completo", max_length=150)
    turma = forms.ModelChoiceField(queryset=Turma.objects.none(), empty_label="Selecione sua turma")
    codigo_turma = forms.CharField(
        label="Código da turma",
        max_length=40,
        required=False,
        help_text="Preencha somente se o professor forneceu um código de ingresso.",
    )
    aceite = forms.BooleanField(label="Li e concordo com as condições de uso formativo.")

    class Meta:
        model = Usuario
        fields = ("rgm", "nome", "turma", "codigo_turma", "password1", "password2", "aceite")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["turma"].queryset = Turma.objects.filter(ativa=True)
        self.fields["password1"].label = "Crie uma senha"
        self.fields["password2"].label = "Confirme a senha"
        self._style_fields()

    def clean_rgm(self):
        rgm = "".join(self.cleaned_data["rgm"].strip().upper().split())
        if Usuario.objects.filter(rgm=rgm).exists():
            raise forms.ValidationError("Este RGM já está cadastrado. Use a tela de login.")
        return rgm

    def clean(self):
        cleaned = super().clean()
        turma = cleaned.get("turma")
        codigo = (cleaned.get("codigo_turma") or "").strip()
        if turma and turma.codigo_ingresso and codigo != turma.codigo_ingresso:
            self.add_error("codigo_turma", "Código de ingresso inválido para a turma selecionada.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rgm = self.cleaned_data["rgm"]
        user.username = user.rgm
        nome = " ".join(self.cleaned_data["nome"].strip().split())
        partes = nome.split(" ", 1)
        user.first_name = partes[0]
        user.last_name = partes[1] if len(partes) > 1 else ""
        user.turma = self.cleaned_data["turma"]
        user.papel = Usuario.Papel.ALUNO
        user.primeiro_acesso_concluido = True
        user.aceite_termos_em = timezone.now()
        if commit:
            user.save()
        return user


class RGMAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="RGM ou usuário", max_length=150)
    password = forms.CharField(label="Senha", strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "username", "placeholder": "Digite seu RGM"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "current-password", "placeholder": "Digite sua senha"}
        )

    def clean_username(self):
        valor = self.cleaned_data["username"].strip()
        usuario = Usuario.objects.filter(Q(username__iexact=valor) | Q(rgm__iexact=valor)).first()
        return usuario.username if usuario else valor


class MensagemChatForm(forms.Form):
    mensagem = forms.CharField(
        label="",
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Digite sua dúvida...",
                "class": "chat-input",
                "aria-label": "Mensagem para a IA Niskier",
            }
        ),
    )
    questao_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    nivel_pista = forms.IntegerField(required=False, min_value=1, max_value=3, initial=1, widget=forms.HiddenInput)


class AjusteNotaForm(StyledFormMixin, forms.Form):
    nota = forms.DecimalField(min_value=0, max_value=10, decimal_places=2)
    justificativa = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), min_length=10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class TemaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Tema
        fields = (
            "titulo",
            "descricao",
            "ordem",
            "ativo",
            "visivel_alunos",
            "liberar_em",
            "tentativas_permitidas",
            "nota_minima",
            "permitir_fontes_externas",
            "referencia_principal",
            "instrucoes_ia",
        )
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "instrucoes_ia": forms.Textarea(attrs={"rows": 4}),
            "liberar_em": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class AulaForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Aula
        fields = "__all__"
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "atividade": forms.Textarea(attrs={"rows": 3}),
            "recursos": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class SlideRevisaoForm(StyledFormMixin, forms.ModelForm):
    pontos_chave_texto = forms.CharField(
        label="Pontos-chave (um por linha)", required=False, widget=forms.Textarea(attrs={"rows": 5})
    )

    class Meta:
        model = SlideRevisao
        fields = ("ordem", "titulo", "conteudo", "pontos_chave_texto", "imagem_url", "tempo_estimado_min", "aprovado")
        widgets = {"conteudo": forms.Textarea(attrs={"rows": 10})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["pontos_chave_texto"].initial = "\n".join(self.instance.pontos_chave or [])
        self._style_fields()

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.pontos_chave = [x.strip() for x in self.cleaned_data["pontos_chave_texto"].splitlines() if x.strip()]
        if commit:
            obj.save()
        return obj


class QuestaoForm(StyledFormMixin, forms.ModelForm):
    alternativas_texto = forms.CharField(
        label="Alternativas",
        required=False,
        help_text="Uma por linha no formato A: texto da alternativa.",
        widget=forms.Textarea(attrs={"rows": 8}),
    )
    erros_texto = forms.CharField(
        label="Erros propositais esperados",
        required=False,
        help_text="Um por linha.",
        widget=forms.Textarea(attrs={"rows": 6}),
    )
    referencias_texto = forms.CharField(
        label="Referências/URLs",
        required=False,
        help_text="Uma URL por linha.",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    class Meta:
        model = Questao
        fields = (
            "tipo",
            "enunciado",
            "alternativas_texto",
            "gabarito",
            "justificativa",
            "erros_texto",
            "dificuldade",
            "nivel_cognitivo",
            "habilidade",
            "referencias_texto",
            "observacao_revisao",
            "status",
        )
        widgets = {
            "enunciado": forms.Textarea(attrs={"rows": 10}),
            "justificativa": forms.Textarea(attrs={"rows": 8}),
            "observacao_revisao": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["alternativas_texto"].initial = "\n".join(
                f"{k}: {v}" for k, v in (self.instance.alternativas or {}).items()
            )
            self.fields["erros_texto"].initial = "\n".join(self.instance.erros_propositais or [])
            refs = []
            for ref in self.instance.referencias or []:
                refs.append(ref.get("url", "") if isinstance(ref, dict) else str(ref))
            self.fields["referencias_texto"].initial = "\n".join(x for x in refs if x)
        self._style_fields()

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        alternativas = {}
        for linha in (cleaned.get("alternativas_texto") or "").splitlines():
            if ":" not in linha:
                continue
            chave, texto = linha.split(":", 1)
            chave = chave.strip().upper()
            if chave in {"A", "B", "C", "D", "E"} and texto.strip():
                alternativas[chave] = texto.strip()
        cleaned["alternativas_json"] = alternativas
        if tipo == Questao.Tipo.OBJETIVA:
            if set(alternativas) != {"A", "B", "C", "D", "E"}:
                self.add_error("alternativas_texto", "Informe exatamente as alternativas A, B, C, D e E.")
            if cleaned.get("gabarito") not in alternativas:
                self.add_error("gabarito", "Selecione um gabarito presente nas alternativas.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.alternativas = self.cleaned_data.get("alternativas_json", {})
        obj.erros_propositais = [x.strip() for x in self.cleaned_data.get("erros_texto", "").splitlines() if x.strip()]
        obj.referencias = [
            {"url": x.strip()} for x in self.cleaned_data.get("referencias_texto", "").splitlines() if x.strip()
        ]
        if commit:
            obj.save()
        return obj


class FonteConhecimentoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FonteConhecimento
        fields = (
            "titulo",
            "url",
            "tipo",
            "conteudo",
            "resumo_auditoria",
            "aprovada",
            "principal",
            "permitir_contexto_url",
        )
        widgets = {
            "conteudo": forms.Textarea(attrs={"rows": 14}),
            "resumo_auditoria": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class AlunoForm(StyledFormMixin, forms.ModelForm):
    nome_completo = forms.CharField(label="Nome completo", max_length=150)

    class Meta:
        model = Usuario
        fields = ("nome_completo", "rgm", "turma", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["nome_completo"].initial = self.instance.nome_exibicao
        self.fields["turma"].queryset = Turma.objects.all()
        self._style_fields()

    def save(self, commit=True):
        obj = super().save(commit=False)
        nome = " ".join(self.cleaned_data["nome_completo"].split())
        partes = nome.split(" ", 1)
        obj.first_name = partes[0]
        obj.last_name = partes[1] if len(partes) > 1 else ""
        obj.papel = Usuario.Papel.ALUNO
        if commit:
            obj.save()
        return obj
