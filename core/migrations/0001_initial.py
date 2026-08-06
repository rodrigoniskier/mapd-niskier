import decimal
import uuid
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="FonteConhecimento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=220)),
                ("url", models.URLField(blank=True)),
                ("conteudo", models.TextField()),
                ("resumo_auditoria", models.TextField(blank=True)),
                ("aprovada", models.BooleanField(default=True)),
                ("principal", models.BooleanField(default=False)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-principal", "titulo"]},
        ),
        migrations.CreateModel(
            name="Tema",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=220)),
                ("slug", models.SlugField(blank=True, max_length=240, unique=True)),
                ("descricao", models.TextField(blank=True)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("ativo", models.BooleanField(default=True)),
                ("pacote_publicado", models.BooleanField(default=False)),
                ("referencia_principal", models.URLField(default="https://mecanismos-medicos-rn-2026.rodrigoniskier.chatgpt.site/")),
            ],
            options={"ordering": ["ordem", "titulo"]},
        ),
        migrations.CreateModel(
            name="Turma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=20)),
                ("semestre", models.CharField(default="2026/2", max_length=20)),
                ("periodo", models.CharField(default="4º", max_length=20)),
                ("ativa", models.BooleanField(default=True)),
            ],
            options={"ordering": ["semestre", "codigo"]},
        ),
        migrations.CreateModel(
            name="Usuario",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("papel", models.CharField(choices=[("ALUNO", "Aluno"), ("PROFESSOR", "Professor")], default="ALUNO", max_length=20)),
                ("rgm", models.CharField(blank=True, max_length=30, null=True, unique=True)),
                ("primeiro_acesso_concluido", models.BooleanField(default=False)),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("turma", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alunos", to="core.turma")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={"abstract": False},
            managers=[("objects", django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name="Aula",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateField(blank=True, null=True)),
                ("horario", models.CharField(blank=True, max_length=50)),
                ("conteudo", models.CharField(max_length=300)),
                ("carga_horaria", models.CharField(blank=True, max_length=30)),
                ("atividade", models.TextField(blank=True)),
                ("recursos", models.TextField(blank=True)),
                ("grupos", models.CharField(blank=True, max_length=200)),
                ("docente", models.CharField(default="Rodrigo Niskier", max_length=120)),
                ("local", models.CharField(blank=True, max_length=120)),
                ("categoria", models.CharField(choices=[("CONTEUDO", "Conteúdo"), ("AVALIACAO", "Avaliação"), ("RECESSO", "Feriado/Recesso"), ("ORGANIZACAO", "Organização/Estudo")], default="CONTEUDO", max_length=20)),
                ("disponivel_para_estudo", models.BooleanField(default=True)),
                ("tema", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="aulas", to="core.tema")),
                ("turma", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aulas", to="core.turma")),
            ],
            options={"ordering": ["data", "id"]},
        ),
        migrations.CreateModel(
            name="Questao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("OBJETIVA", "Objetiva"), ("DISCURSIVA", "Discursiva")], max_length=20)),
                ("enunciado", models.TextField()),
                ("alternativas", models.JSONField(blank=True, default=dict)),
                ("gabarito", models.CharField(blank=True, max_length=1)),
                ("justificativa", models.TextField(blank=True)),
                ("erros_propositais", models.JSONField(blank=True, default=list)),
                ("dificuldade", models.CharField(default="intermediária", max_length=30)),
                ("nivel_cognitivo", models.CharField(default="aplicação", max_length=100)),
                ("status", models.CharField(choices=[("RASCUNHO", "Rascunho"), ("APROVADA", "Aprovada"), ("ARQUIVADA", "Arquivada")], default="RASCUNHO", max_length=20)),
                ("criada_por_ia", models.BooleanField(default=False)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("tema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questoes", to="core.tema")),
            ],
            options={"ordering": ["tema", "tipo", "id"]},
        ),
        migrations.CreateModel(
            name="SlideRevisao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordem", models.PositiveSmallIntegerField(default=1)),
                ("titulo", models.CharField(max_length=200)),
                ("conteudo", models.TextField()),
                ("aprovado", models.BooleanField(default=False)),
                ("tema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slides", to="core.tema")),
            ],
            options={"ordering": ["ordem"]},
        ),
        migrations.CreateModel(
            name="Tentativa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("iniciada_em", models.DateTimeField(auto_now_add=True)),
                ("concluida_em", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("EM_ANDAMENTO", "Em andamento"), ("CONCLUIDA", "Concluída"), ("REVISAO", "Aguardando revisão")], default="EM_ANDAMENTO", max_length=20)),
                ("nota_objetiva", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=4)),
                ("nota_discursiva", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=4)),
                ("nota_total", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=4)),
                ("feedback", models.TextField(blank=True)),
                ("codigo_comprovante", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("quantidade_pistas", models.PositiveIntegerField(default=0)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tentativas", to=settings.AUTH_USER_MODEL)),
                ("tema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tentativas", to="core.tema")),
            ],
            options={"ordering": ["-iniciada_em"]},
        ),
        migrations.CreateModel(
            name="QuestaoTentativa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordem", models.PositiveSmallIntegerField()),
                ("valor", models.DecimalField(decimal_places=2, max_digits=3)),
                ("questao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.questao")),
                ("tentativa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="itens", to="core.tentativa")),
            ],
            options={"ordering": ["ordem"]},
        ),
        migrations.CreateModel(
            name="Resposta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("alternativa_marcada", models.CharField(blank=True, max_length=1)),
                ("resposta_textual", models.TextField(blank=True)),
                ("correta", models.BooleanField(blank=True, null=True)),
                ("nota", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=3)),
                ("comentario", models.TextField(blank=True)),
                ("questao", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.questao")),
                ("tentativa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="respostas", to="core.tentativa")),
            ],
        ),
        migrations.CreateModel(
            name="SessaoChat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contexto", models.CharField(choices=[("PLANTAO", "Plantão"), ("QUESTAO", "Questão")], max_length=20)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessoes_chat", to=settings.AUTH_USER_MODEL)),
                ("tema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessoes_chat", to="core.tema")),
                ("tentativa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="sessoes_chat", to="core.tentativa")),
            ],
        ),
        migrations.CreateModel(
            name="MensagemChat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("autor", models.CharField(choices=[("ALUNO", "Aluno"), ("IA", "IA Niskier")], max_length=10)),
                ("texto", models.TextField()),
                ("fontes", models.JSONField(blank=True, default=list)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("sessao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mensagens", to="core.sessaochat")),
            ],
            options={"ordering": ["criada_em"]},
        ),
        migrations.CreateModel(
            name="AuditoriaNota",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nota_anterior", models.DecimalField(decimal_places=2, max_digits=4)),
                ("nota_nova", models.DecimalField(decimal_places=2, max_digits=4)),
                ("justificativa", models.TextField()),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("alterada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("tentativa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="auditorias", to="core.tentativa")),
            ],
        ),
        migrations.AddConstraint(
            model_name="turma",
            constraint=models.UniqueConstraint(fields=("codigo", "semestre"), name="turma_codigo_semestre_unico"),
        ),
        migrations.AddConstraint(
            model_name="sliderevisao",
            constraint=models.UniqueConstraint(fields=("tema", "ordem"), name="slide_tema_ordem_unico"),
        ),
        migrations.AddConstraint(
            model_name="questaotentativa",
            constraint=models.UniqueConstraint(fields=("tentativa", "ordem"), name="tentativa_ordem_unica"),
        ),
        migrations.AddConstraint(
            model_name="questaotentativa",
            constraint=models.UniqueConstraint(fields=("tentativa", "questao"), name="tentativa_questao_unica"),
        ),
        migrations.AddConstraint(
            model_name="resposta",
            constraint=models.UniqueConstraint(fields=("tentativa", "questao"), name="resposta_tentativa_questao_unica"),
        ),
    ]
