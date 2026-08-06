import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Turma(models.Model):
    codigo = models.CharField(max_length=20)
    semestre = models.CharField(max_length=20, default="2026/2")
    periodo = models.CharField(max_length=20, default="4º")
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["semestre", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["codigo", "semestre"], name="turma_codigo_semestre_unico")
        ]

    def __str__(self):
        return f"Turma {self.codigo} — {self.semestre}"


class Usuario(AbstractUser):
    class Papel(models.TextChoices):
        ALUNO = "ALUNO", "Aluno"
        PROFESSOR = "PROFESSOR", "Professor"

    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.ALUNO)
    turma = models.ForeignKey(Turma, on_delete=models.SET_NULL, null=True, blank=True, related_name="alunos")
    rgm = models.CharField(max_length=30, unique=True, null=True, blank=True)
    primeiro_acesso_concluido = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.rgm:
            self.rgm = self.rgm.strip().upper()
            self.username = self.rgm
        super().save(*args, **kwargs)

    @property
    def nome_exibicao(self):
        return self.get_full_name().strip() or self.username

    def __str__(self):
        return f"{self.nome_exibicao} ({self.rgm or self.username})"


class Tema(models.Model):
    titulo = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    descricao = models.TextField(blank=True)
    ordem = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    pacote_publicado = models.BooleanField(default=False)
    referencia_principal = models.URLField(
        default="https://mecanismos-medicos-rn-2026.rodrigoniskier.chatgpt.site/"
    )

    class Meta:
        ordering = ["ordem", "titulo"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titulo)[:220] or "tema"
            slug = base
            n = 2
            while Tema.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("escolher_modo", args=[self.slug])


class Aula(models.Model):
    class Categoria(models.TextChoices):
        CONTEUDO = "CONTEUDO", "Conteúdo"
        AVALIACAO = "AVALIACAO", "Avaliação"
        RECESSO = "RECESSO", "Feriado/Recesso"
        ORGANIZACAO = "ORGANIZACAO", "Organização/Estudo"

    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name="aulas")
    tema = models.ForeignKey(Tema, on_delete=models.SET_NULL, null=True, blank=True, related_name="aulas")
    data = models.DateField(null=True, blank=True)
    horario = models.CharField(max_length=50, blank=True)
    conteudo = models.CharField(max_length=300)
    carga_horaria = models.CharField(max_length=30, blank=True)
    atividade = models.TextField(blank=True)
    recursos = models.TextField(blank=True)
    grupos = models.CharField(max_length=200, blank=True)
    docente = models.CharField(max_length=120, default="Rodrigo Niskier")
    local = models.CharField(max_length=120, blank=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.CONTEUDO)
    disponivel_para_estudo = models.BooleanField(default=True)

    class Meta:
        ordering = ["data", "id"]

    def __str__(self):
        return f"{self.turma} — {self.data or 'A definir'} — {self.conteudo}"


class SlideRevisao(models.Model):
    tema = models.ForeignKey(Tema, on_delete=models.CASCADE, related_name="slides")
    ordem = models.PositiveSmallIntegerField(default=1)
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    aprovado = models.BooleanField(default=False)

    class Meta:
        ordering = ["ordem"]
        constraints = [
            models.UniqueConstraint(fields=["tema", "ordem"], name="slide_tema_ordem_unico")
        ]

    def __str__(self):
        return f"{self.tema} — slide {self.ordem}"


class Questao(models.Model):
    class Tipo(models.TextChoices):
        OBJETIVA = "OBJETIVA", "Objetiva"
        DISCURSIVA = "DISCURSIVA", "Discursiva"

    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        APROVADA = "APROVADA", "Aprovada"
        ARQUIVADA = "ARQUIVADA", "Arquivada"

    tema = models.ForeignKey(Tema, on_delete=models.CASCADE, related_name="questoes")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    enunciado = models.TextField()
    alternativas = models.JSONField(default=dict, blank=True)
    gabarito = models.CharField(max_length=1, blank=True)
    justificativa = models.TextField(blank=True)
    erros_propositais = models.JSONField(default=list, blank=True)
    dificuldade = models.CharField(max_length=30, default="intermediária")
    nivel_cognitivo = models.CharField(max_length=100, default="aplicação")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    criada_por_ia = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tema", "tipo", "id"]

    def __str__(self):
        return f"{self.tema} — {self.get_tipo_display()} #{self.pk or 'nova'}"


class Tentativa(models.Model):
    class Status(models.TextChoices):
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        REVISAO = "REVISAO", "Aguardando revisão"

    aluno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="tentativas")
    tema = models.ForeignKey(Tema, on_delete=models.CASCADE, related_name="tentativas")
    iniciada_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EM_ANDAMENTO)
    nota_objetiva = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.00"))
    nota_discursiva = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.00"))
    nota_total = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.00"))
    feedback = models.TextField(blank=True)
    codigo_comprovante = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    quantidade_pistas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-iniciada_em"]

    def __str__(self):
        return f"{self.aluno} — {self.tema} — {self.nota_total}"

    def recalcular_nota(self):
        respostas = self.respostas.select_related("questao")
        objetiva = sum((r.nota for r in respostas if r.questao.tipo == Questao.Tipo.OBJETIVA), Decimal("0"))
        discursiva = sum((r.nota for r in respostas if r.questao.tipo == Questao.Tipo.DISCURSIVA), Decimal("0"))
        self.nota_objetiva = objetiva
        self.nota_discursiva = discursiva
        self.nota_total = min(Decimal("10.00"), objetiva + discursiva)
        self.save(update_fields=["nota_objetiva", "nota_discursiva", "nota_total"])


class QuestaoTentativa(models.Model):
    tentativa = models.ForeignKey(Tentativa, on_delete=models.CASCADE, related_name="itens")
    questao = models.ForeignKey(Questao, on_delete=models.PROTECT)
    ordem = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        ordering = ["ordem"]
        constraints = [
            models.UniqueConstraint(fields=["tentativa", "ordem"], name="tentativa_ordem_unica"),
            models.UniqueConstraint(fields=["tentativa", "questao"], name="tentativa_questao_unica"),
        ]

    def __str__(self):
        return f"{self.tentativa} — Q{self.ordem}"


class Resposta(models.Model):
    tentativa = models.ForeignKey(Tentativa, on_delete=models.CASCADE, related_name="respostas")
    questao = models.ForeignKey(Questao, on_delete=models.PROTECT)
    alternativa_marcada = models.CharField(max_length=1, blank=True)
    resposta_textual = models.TextField(blank=True)
    correta = models.BooleanField(null=True, blank=True)
    nota = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))
    comentario = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tentativa", "questao"], name="resposta_tentativa_questao_unica")
        ]

    def __str__(self):
        return f"{self.tentativa} — {self.questao}"


class FonteConhecimento(models.Model):
    titulo = models.CharField(max_length=220)
    url = models.URLField(blank=True)
    conteudo = models.TextField()
    resumo_auditoria = models.TextField(blank=True)
    aprovada = models.BooleanField(default=True)
    principal = models.BooleanField(default=False)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-principal", "titulo"]

    def __str__(self):
        return self.titulo


class SessaoChat(models.Model):
    class Contexto(models.TextChoices):
        PLANTAO = "PLANTAO", "Plantão"
        QUESTAO = "QUESTAO", "Questão"

    aluno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="sessoes_chat")
    tema = models.ForeignKey(Tema, on_delete=models.CASCADE, related_name="sessoes_chat")
    tentativa = models.ForeignKey(Tentativa, on_delete=models.CASCADE, null=True, blank=True, related_name="sessoes_chat")
    contexto = models.CharField(max_length=20, choices=Contexto.choices)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.aluno} — {self.tema} — {self.contexto}"


class MensagemChat(models.Model):
    class Autor(models.TextChoices):
        ALUNO = "ALUNO", "Aluno"
        IA = "IA", "IA Niskier"

    sessao = models.ForeignKey(SessaoChat, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.CharField(max_length=10, choices=Autor.choices)
    texto = models.TextField()
    fontes = models.JSONField(default=list, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criada_em"]

    def __str__(self):
        return f"{self.sessao} — {self.autor}"


class AuditoriaNota(models.Model):
    tentativa = models.ForeignKey(Tentativa, on_delete=models.CASCADE, related_name="auditorias")
    alterada_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    nota_anterior = models.DecimalField(max_digits=4, decimal_places=2)
    nota_nova = models.DecimalField(max_digits=4, decimal_places=2)
    justificativa = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tentativa} — {self.nota_anterior} → {self.nota_nova}"
