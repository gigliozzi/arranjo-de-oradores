from django import forms
from django.contrib import admin, messages
from django.db.models import Q

from .models import (
    Congregacao,
    Discurso,
    EventoStatusMensagem,
    Notificacao,
    Orador,
    RespostaNotificacao,
    TemaDiscurso,
)
from .services import processar_notificacao
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


@admin.register(TemaDiscurso)
class TemaDiscursoAdmin(admin.ModelAdmin):
    list_display = ("numero", "titulo", "ativo")
    list_filter = ("ativo",)
    search_fields = ("=numero", "titulo")
    list_editable = ("ativo",)


class NotificacaoInline(admin.TabularInline):
    model = Notificacao
    extra = 0
    readonly_fields = ("data_envio", "message_id", "zaap_id", "status_whatsapp", "resposta_api")


class DiscursoAdminForm(forms.ModelForm):
    class Meta:
        model = Discurso
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = TemaDiscurso.objects.filter(ativo=True)
        if self.instance and self.instance.tema_predefinido_id:
            queryset = TemaDiscurso.objects.filter(
                Q(ativo=True) | Q(pk=self.instance.tema_predefinido_id)
            )
        self.fields["tema_predefinido"].queryset = queryset.order_by("numero")


@admin.register(Discurso)
class DiscursoAdmin(admin.ModelAdmin):
    form = DiscursoAdminForm
    list_display = (
        "data",
        "hora",
        "tema_do_discurso",
        "orador",
        "congregacao_destino",
        "status",
    )
    list_filter = ("data", "orador", "congregacao_destino", "tema_predefinido", "status")
    search_fields = (
        "tema",
        "=tema_predefinido__numero",
        "tema_predefinido__titulo",
        "orador__nome",
        "congregacao_destino__nome",
        "congregacao_destino__cidade",
    )
    date_hierarchy = "data"
    autocomplete_fields = ("orador", "tema_predefinido", "congregacao_destino")
    inlines = [NotificacaoInline]

    @admin.display(description="Tema", ordering="tema_predefinido__numero")
    def tema_do_discurso(self, obj):
        return obj.tema_para_exibicao

    class Media:
        css = {"all": ("discursos/admin/discurso_form.css",)}


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = (
        "data_prevista",
        "discurso",
        "marco",
        "status_envio",
        "status_whatsapp",
        "data_envio",
    )
    list_filter = (
        "data_prevista",
        "marco",
        "status_envio",
        "status_whatsapp",
        "discurso__orador",
        "discurso__congregacao_destino",
        "discurso__status",
    )
    search_fields = (
        "discurso__tema",
        "=discurso__tema_predefinido__numero",
        "discurso__tema_predefinido__titulo",
        "discurso__orador__nome",
        "discurso__congregacao_destino__nome",
        "resposta_api",
        "message_id",
        "zaap_id",
        "telefone_destino",
    )
    autocomplete_fields = ("discurso",)
    actions = ("enviar_notificacoes_selecionadas", "marcar_como_pendente")
    readonly_fields = (
        "data_envio",
        "provedor",
        "telefone_destino",
        "message_id",
        "zaap_id",
        "status_whatsapp",
        "data_status_whatsapp",
    )

    class Media:
        js = ("discursos/admin/notificacao_actions.js",)

    @admin.action(description="Enviar/reprocessar notificações selecionadas")
    def enviar_notificacoes_selecionadas(self, request, queryset):
        enviadas = 0
        erros = 0
        ignoradas = 0

        for notificacao in queryset.select_related(
            "discurso",
            "discurso__orador",
            "discurso__congregacao_destino",
        ):
            if notificacao.status_envio == Notificacao.StatusEnvio.ENVIADO:
                ignoradas += 1
                continue

            resultado = processar_notificacao(notificacao)
            if resultado.status_envio == Notificacao.StatusEnvio.ENVIADO:
                enviadas += 1
            elif resultado.status_envio == Notificacao.StatusEnvio.ERRO:
                erros += 1

        self.message_user(
            request,
            f"Processamento concluído: {enviadas} enviadas, {erros} erros, {ignoradas} ignoradas.",
            level=messages.SUCCESS if erros == 0 else messages.WARNING,
        )

    @admin.action(description="Marcar selecionadas como pendente")
    def marcar_como_pendente(self, request, queryset):
        atualizadas = queryset.exclude(status_envio=Notificacao.StatusEnvio.ENVIADO).update(
            status_envio=Notificacao.StatusEnvio.PENDENTE,
            data_envio=None,
        )
        self.message_user(request, f"{atualizadas} notificações marcadas como pendente.")


@admin.register(RespostaNotificacao)
class RespostaNotificacaoAdmin(admin.ModelAdmin):
    list_display = ("data_recebimento", "telefone", "nome_contato", "notificacao", "mensagem")
    list_filter = ("data_recebimento",)
    search_fields = (
        "telefone",
        "nome_contato",
        "mensagem",
        "message_id",
        "reference_message_id",
        "notificacao__discurso__orador__nome",
    )
    autocomplete_fields = ("notificacao",)
    readonly_fields = (
        "notificacao",
        "telefone",
        "nome_contato",
        "mensagem",
        "message_id",
        "reference_message_id",
        "data_recebimento",
        "payload_api",
    )


@admin.register(EventoStatusMensagem)
class EventoStatusMensagemAdmin(admin.ModelAdmin):
    list_display = ("data_evento", "status", "telefone", "message_id", "notificacao")
    list_filter = ("status", "data_evento")
    search_fields = ("telefone", "message_id", "notificacao__discurso__orador__nome")
    autocomplete_fields = ("notificacao",)
    readonly_fields = ("notificacao", "status", "telefone", "message_id", "data_evento", "payload_api")
