from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Aula, AuditoriaNota, FonteConhecimento, MensagemChat, Questao, QuestaoTentativa,
    Resposta, SessaoChat, SlideRevisao, Tema, Tentativa, Turma, Usuario
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("MAPD", {"fields": ("rgm", "papel", "turma", "primeiro_acesso_concluido")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("MAPD", {"fields": ("rgm", "papel", "turma", "primeiro_acesso_concluido")}),
    )
    list_display = ("username", "first_name", "rgm", "papel", "turma", "is_staff")
    list_filter = ("papel", "turma", "is_staff")
    search_fields = ("username", "rgm", "first_name", "last_name")


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "semestre", "periodo", "ativa")
    list_filter = ("semestre", "ativa")


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "ordem", "ativo", "pacote_publicado")
    list_editable = ("ordem", "ativo", "pacote_publicado")
    prepopulated_fields = {"slug": ("titulo",)}
    search_fields = ("titulo",)


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
    list_display = ("id", "tema", "tipo", "dificuldade", "nivel_cognitivo", "status", "criada_por_ia")
    list_filter = ("tema", "tipo", "status", "dificuldade", "criada_por_ia")
    search_fields = ("enunciado", "justificativa")
    list_editable = ("status",)


class RespostaInline(admin.TabularInline):
    model = Resposta
    extra = 0
    readonly_fields = ("questao", "alternativa_marcada", "resposta_textual", "correta")


@admin.register(Tentativa)
class TentativaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "tema", "status", "nota_objetiva", "nota_discursiva", "nota_total", "concluida_em")
    list_filter = ("status", "tema", "aluno__turma")
    search_fields = ("aluno__rgm", "aluno__first_name")
    inlines = [RespostaInline]


@admin.register(FonteConhecimento)
class FonteConhecimentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "principal", "aprovada", "atualizada_em")
    list_filter = ("principal", "aprovada")
    search_fields = ("titulo", "conteudo", "url")


admin.site.register(QuestaoTentativa)
admin.site.register(Resposta)
admin.site.register(SessaoChat)
admin.site.register(MensagemChat)
admin.site.register(AuditoriaNota)

admin.site.site_header = "MAPD Niskier — Administração"
admin.site.site_title = "MAPD Niskier"
admin.site.index_title = "Gestão acadêmica"
