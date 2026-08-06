from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
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


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("MAPD", {"fields": ("rgm", "papel", "turma", "primeiro_acesso_concluido", "aceite_termos_em")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("MAPD", {"fields": ("rgm", "papel", "turma", "primeiro_acesso_concluido")}),
    )
    list_display = ("username", "first_name", "last_name", "rgm", "papel", "turma", "is_staff", "is_active")
    list_filter = ("papel", "turma", "is_staff", "is_active")
    search_fields = ("username", "rgm", "first_name", "last_name", "email")


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "semestre", "periodo", "ativa")
    list_filter = ("semestre", "ativa")
    search_fields = ("codigo", "nome")


class SlideInline(admin.StackedInline):
    model = SlideRevisao
    extra = 0


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "ordem", "ativo", "visivel_alunos", "pacote_publicado", "liberar_em")
    list_editable = ("ordem", "ativo", "visivel_alunos", "pacote_publicado")
    prepopulated_fields = {"slug": ("titulo",)}
    search_fields = ("titulo", "descricao")
    inlines = [SlideInline]


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("data", "turma", "conteudo", "categoria", "disponivel_para_estudo", "local")
    list_filter = ("turma", "categoria", "disponivel_para_estudo")
    search_fields = ("conteudo", "atividade")


@admin.register(SlideRevisao)
class SlideRevisaoAdmin(admin.ModelAdmin):
    list_display = ("tema", "ordem", "titulo", "aprovado")
    list_filter = ("aprovado", "tema")
    list_editable = ("aprovado",)


@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tema",
        "tipo",
        "dificuldade",
        "nivel_cognitivo",
        "status",
        "criada_por_ia",
        "revisada_por",
    )
    list_filter = ("tema", "tipo", "status", "dificuldade", "criada_por_ia")
    search_fields = ("enunciado", "justificativa", "habilidade")
    list_editable = ("status",)
    readonly_fields = ("criada_em", "atualizada_em", "revisada_em")


class RespostaInline(admin.TabularInline):
    model = Resposta
    extra = 0
    readonly_fields = ("questao", "alternativa_marcada", "resposta_textual", "correta", "salva_em")


@admin.register(Tentativa)
class TentativaAdmin(admin.ModelAdmin):
    list_display = (
        "aluno",
        "tema",
        "status",
        "nota_objetiva",
        "nota_discursiva",
        "nota_total",
        "quantidade_pistas",
        "concluida_em",
    )
    list_filter = ("status", "tema", "aluno__turma", "nivel_adaptativo")
    search_fields = ("aluno__rgm", "aluno__first_name", "aluno__last_name")
    inlines = [RespostaInline]
    readonly_fields = ("codigo_comprovante", "iniciada_em", "concluida_em")


@admin.register(FonteConhecimento)
class FonteConhecimentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "principal", "aprovada", "auditada_em", "atualizada_em")
    list_filter = ("tipo", "principal", "aprovada")
    search_fields = ("titulo", "conteudo", "url")


@admin.register(TarefaIA)
class TarefaIAAdmin(admin.ModelAdmin):
    list_display = ("tipo", "status", "tema", "tentativa", "solicitada_por", "criada_em")
    list_filter = ("tipo", "status")
    readonly_fields = ("criada_em", "iniciada_em", "concluida_em")


@admin.register(ConfiguracaoPlataforma)
class ConfiguracaoPlataformaAdmin(admin.ModelAdmin):
    list_display = ("nome", "instituicao", "ativo", "atualizado_em")


admin.site.register(QuestaoTentativa)
admin.site.register(Resposta)
admin.site.register(RevisaoProgresso)
admin.site.register(SessaoChat)
admin.site.register(MensagemChat)
admin.site.register(AuditoriaNota)
admin.site.register(RegistroAuditoria)

admin.site.site_header = "MAPD Niskier — Administração"
admin.site.site_title = "MAPD Niskier"
admin.site.index_title = "Gestão acadêmica"
