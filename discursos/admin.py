from django.contrib import admin, messages

from .models import Congregacao, Discurso, Notificacao, Orador
from .services import preencher_endereco_por_cep


@admin.register(Orador)
class OradorAdmin(admin.ModelAdmin):
    list_display = ("nome", "celular", "congregacao_origem", "ativo")
    list_filter = ("ativo", "congregacao_origem")
    search_fields = ("nome", "celular", "congregacao_origem")


@admin.register(Congregacao)
class CongregacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cidade", "estado", "bairro", "cep", "responsavel", "telefone")
    list_filter = ("estado", "cidade")
    search_fields = (
        "nome",
        "cep",
        "logradouro",
        "bairro",
        "cidade",
        "estado",
        "responsavel",
        "telefone",
    )
    fieldsets = (
        (None, {"fields": ("nome", "responsavel", "telefone")}),
        (
            "Endereço",
            {
                "fields": (
                    "cep",
                    "logradouro",
                    "numero",
                    "complemento",
                    "bairro",
                    "cidade",
                    "estado",
                )
            },
        ),
    )

    class Media:
        js = ("discursos/admin/congregacao_cep.js",)

    def save_model(self, request, obj, form, change):
        if obj.cep and not obj.logradouro:
            try:
                preencher_endereco_por_cep(obj)
            except ValueError as exc:
                self.message_user(
                    request,
                    f"Não foi possível buscar o CEP: {exc}",
                    level=messages.WARNING,
                )
            else:
                self.message_user(request, "Endereço preenchido a partir do CEP.")
        super().save_model(request, obj, form, change)


class NotificacaoInline(admin.TabularInline):
    model = Notificacao
    extra = 0
    readonly_fields = ("data_envio", "resposta_api")


@admin.register(Discurso)
class DiscursoAdmin(admin.ModelAdmin):
    list_display = (
        "data",
        "hora",
        "tema",
        "orador",
        "congregacao_destino",
        "status",
    )
    list_filter = ("data", "orador", "congregacao_destino", "status")
    search_fields = (
        "tema",
        "orador__nome",
        "congregacao_destino__nome",
        "congregacao_destino__cidade",
    )
    date_hierarchy = "data"
    autocomplete_fields = ("orador", "congregacao_destino")
    inlines = [NotificacaoInline]


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = (
        "data_prevista",
        "discurso",
        "marco",
        "status_envio",
        "data_envio",
    )
    list_filter = (
        "data_prevista",
        "marco",
        "status_envio",
        "discurso__orador",
        "discurso__congregacao_destino",
        "discurso__status",
    )
    search_fields = (
        "discurso__tema",
        "discurso__orador__nome",
        "discurso__congregacao_destino__nome",
        "resposta_api",
    )
    autocomplete_fields = ("discurso",)
    readonly_fields = ("data_envio",)
