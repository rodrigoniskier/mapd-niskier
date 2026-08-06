from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Turma, Usuario


class PrimeiroAcessoForm(UserCreationForm):
    rgm = forms.CharField(label="RGM", max_length=30)
    nome = forms.CharField(label="Nome completo", max_length=150)
    turma = forms.ModelChoiceField(queryset=Turma.objects.none(), empty_label="Selecione sua turma")

    class Meta:
        model = Usuario
        fields = ("rgm", "nome", "turma", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["turma"].queryset = Turma.objects.filter(ativa=True)
        self.fields["password1"].label = "Crie uma senha"
        self.fields["password2"].label = "Confirme a senha"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_rgm(self):
        rgm = self.cleaned_data["rgm"].strip().upper()
        if Usuario.objects.filter(rgm=rgm).exists():
            raise forms.ValidationError("Este RGM já está cadastrado. Use a tela de login.")
        return rgm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rgm = self.cleaned_data["rgm"]
        user.username = user.rgm
        user.first_name = self.cleaned_data["nome"].strip()
        user.turma = self.cleaned_data["turma"]
        user.papel = Usuario.Papel.ALUNO
        user.primeiro_acesso_concluido = True
        if commit:
            user.save()
        return user


class RGMAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="RGM", max_length=30)
    password = forms.CharField(label="Senha", strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control", "autocomplete": "username"})
        self.fields["password"].widget.attrs.update({"class": "form-control", "autocomplete": "current-password"})

    def clean_username(self):
        return self.cleaned_data["username"].strip().upper()


class MensagemChatForm(forms.Form):
    mensagem = forms.CharField(
        label="",
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Digite sua dúvida...", "class": "chat-input"}),
    )


class AjusteNotaForm(forms.Form):
    nota = forms.DecimalField(min_value=0, max_value=10, decimal_places=2)
    justificativa = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), min_length=10)
