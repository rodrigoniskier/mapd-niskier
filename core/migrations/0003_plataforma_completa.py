import decimal
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0002_alter_usuario_options")]

    operations = [
        migrations.AddField(
            model_name="turma",
            name="codigo_ingresso",
            field=models.CharField(blank=True, help_text="Opcional. Quando preenchido, será exigido no primeiro acesso do aluno.", max_length=40),
        ),
        migrations.AddField(model_name="turma", name="nome", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="usuario", name="aceite_termos_em", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="tema", name="instrucoes_ia", field=models.TextField(blank=True)),
        migrations.AddField(model_name="tema", name="liberar_em", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="tema",
            name="nota_minima",
            field=models.DecimalField(decimal_places=2, default=decimal.Decimal("6.00"), max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)]),
        ),
        migrations.AddField(model_name="tema", name="permitir_fontes_externas", field=models.BooleanField(default=True)),
        migrations.AddField(
            model_name="tema",
            name="tentativas_permitidas",
            field=models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AddField(model_name="tema", name="visivel_alunos", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="sliderevisao", name="imagem_url", field=models.URLField(blank=True)),
        migrations.AddField(model_name="sliderevisao", name="pontos_chave", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="sliderevisao", name="tempo_estimado_min", field=models.PositiveSmallIntegerField(default=2)),
        migrations.AlterField(
            model_name="sliderevisao",
            name="ordem",
            field=models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3)]),
        ),
        migrations.CreateModel(
            name="RevisaoProgresso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("iniciada_em", models.DateTimeField(auto_now_add=True)),
                ("atualizada_em", models.DateTimeField(auto_now=True)),
                ("concluida_em", models.DateTimeField(blank=True, null=True)),
                ("slide_atual", models.PositiveSmallIntegerField(default=1)),
                ("aluno", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisoes", to=settings.AUTH_USER_MODEL)),
                ("tema", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="revisoes", to="core.tema")),
            ],
        ),
        migrations.AddConstraint(
            model_name="revisaoprogresso",
            constraint=models.UniqueConstraint(fields=("aluno", "tema"), name="revisao_aluno_tema_unica"),
        ),
        migrations.AddField(model_name="questao", name="habilidade", field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name="questao", name="observacao_revisao", field=models.TextField(blank=True)),
        migrations.AddField(model_name="questao", name="referencias", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(
            model_name="questao",
            name="atualizada_em",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="questao",
            name="revisada_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="questao",
            name="revisada_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="questoes_revisadas", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(model_name="tentativa", name="duracao_segundos", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="tentativa", name="feedback_gerado_em", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="tentativa", name="nivel_adaptativo", field=models.CharField(default="equilibrado", max_length=40)),
        migrations.AddField(model_name="tentativa", name="versao", field=models.PositiveSmallIntegerField(default=1)),
        migrations.AlterField(
            model_name="tentativa",
            name="status",
            field=models.CharField(choices=[("EM_ANDAMENTO", "Em andamento"), ("PROCESSANDO", "Gerando feedback"), ("CONCLUIDA", "Concluída"), ("REVISAO", "Aguardando revisão")], default="EM_ANDAMENTO", max_length=20),
        ),
        migrations.AddField(model_name="questaotentativa", name="ajuda_usada", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(
            model_name="resposta",
            name="salva_em",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(model_name="fonteconhecimento", name="conteudo", field=models.TextField(blank=True)),
        migrations.AddField(model_name="fonteconhecimento", name="auditada_em", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="fonteconhecimento", name="permitir_contexto_url", field=models.BooleanField(default=True)),
        migrations.AddField(
            model_name="fonteconhecimento",
            name="tipo",
            field=models.CharField(choices=[("LIVRO", "Livro/base principal"), ("DIRETRIZ", "Diretriz"), ("ARTIGO", "Artigo científico"), ("INSTITUCIONAL", "Institucional"), ("OUTRA", "Outra")], default="OUTRA", max_length=20),
        ),
        migrations.AddField(model_name="sessaochat", name="ativa", field=models.BooleanField(default=True)),
        migrations.AddField(
            model_name="sessaochat",
            name="atualizada_em",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="mensagemchat",
            name="autor",
            field=models.CharField(choices=[("ALUNO", "Aluno"), ("IA", "IA Niskier"), ("SISTEMA", "Sistema")], max_length=10),
        ),
        migrations.AddField(model_name="mensagemchat", name="nivel_pista", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(
            model_name="mensagemchat",
            name="questao",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="core.questao"),
        ),
        migrations.CreateModel(
            name="ConfiguracaoPlataforma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(default="MAPD Niskier", max_length=120)),
                ("subtitulo", models.CharField(default="Mecanismos de Agressão, Patológicos e de Defesa", max_length=220)),
                ("instituicao", models.CharField(default="Medicina — UNIPÊ", max_length=120)),
                ("aviso_avaliacao", models.CharField(default="Não precisa buscar as respostas em outra IA, cole o enunciado aqui que eu te ajudo a responder.", max_length=300)),
                ("termos_primeiro_acesso", models.TextField(default="Esta plataforma é um ambiente de apoio formativo. As respostas da IA devem ser analisadas criticamente e não substituem orientação docente nem fontes científicas primárias.")),
                ("ativo", models.BooleanField(default=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "configuração da plataforma", "verbose_name_plural": "configurações da plataforma"},
        ),
        migrations.CreateModel(
            name="RegistroAuditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("acao", models.CharField(max_length=100)),
                ("objeto", models.CharField(blank=True, max_length=100)),
                ("objeto_id", models.CharField(blank=True, max_length=80)),
                ("detalhes", models.JSONField(blank=True, default=dict)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-criada_em"]},
        ),
        migrations.CreateModel(
            name="TarefaIA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("PACOTE", "Gerar pacote"), ("FEEDBACK", "Gerar feedback")], max_length=20)),
                ("status", models.CharField(choices=[("PENDENTE", "Pendente"), ("PROCESSANDO", "Processando"), ("CONCLUIDA", "Concluída"), ("ERRO", "Erro")], default="PENDENTE", max_length=20)),
                ("mensagem_erro", models.TextField(blank=True)),
                ("criada_em", models.DateTimeField(auto_now_add=True)),
                ("iniciada_em", models.DateTimeField(blank=True, null=True)),
                ("concluida_em", models.DateTimeField(blank=True, null=True)),
                ("solicitada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("tema", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="core.tema")),
                ("tentativa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="core.tentativa")),
            ],
            options={"ordering": ["-criada_em"]},
        ),
    ]
