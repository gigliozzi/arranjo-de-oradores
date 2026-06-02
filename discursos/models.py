from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Orador(models.Model):
    nome = models.CharField(max_length=150)
    celular = models.CharField(max_length=30)
    congregacao_origem = models.CharField("congregação de origem", max_length=150)
    observacoes = models.TextField("observações", blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "orador"
        verbose_name_plural = "oradores"

    def __str__(self):
        return self.nome


class Congregacao(models.Model):
    nome = models.CharField(max_length=150)
    cep = models.CharField("CEP", max_length=9, blank=True)
    logradouro = models.CharField(max_length=200, blank=True)
    numero = models.CharField("número", max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    responsavel = models.CharField("responsável", max_length=150, blank=True)
    telefone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "congregação"
        verbose_name_plural = "congregações"

    def __str__(self):
        local = f"{self.cidade}/{self.estado}" if self.cidade and self.estado else ""
        return f"{self.nome} - {local}" if local else self.nome

    @property
    def endereco_formatado(self):
        partes = []
        if self.logradouro:
            linha = self.logradouro
            if self.numero:
                linha = f"{linha}, {self.numero}"
            partes.append(linha)
        if self.complemento:
            partes.append(self.complemento)
        if self.bairro:
            partes.append(self.bairro)
        cidade_estado = "/".join(parte for parte in [self.cidade, self.estado] if parte)
        if cidade_estado:
            partes.append(cidade_estado)
        if self.cep:
            partes.append(f"CEP {self.cep}")
        return " - ".join(partes)


class TemaDiscurso(models.Model):
    numero = models.PositiveIntegerField("número", unique=True)
    titulo = models.CharField("título", max_length=255)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "tema de discurso"
        verbose_name_plural = "temas de discursos"

    def __str__(self):
        return f"{self.numero} - {self.titulo}"


class Discurso(models.Model):
    class Status(models.TextChoices):
        AGENDADO = "agendado", "Agendado"
        CONFIRMADO = "confirmado", "Confirmado"
        CANCELADO = "cancelado", "Cancelado"
        REALIZADO = "realizado", "Realizado"

    orador = models.ForeignKey(Orador, on_delete=models.PROTECT, related_name="discursos")
    tema_predefinido = models.ForeignKey(
        TemaDiscurso,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discursos",
        verbose_name="tema predefinido",
    )
    tema = models.CharField("tema manual", max_length=200, blank=True)
    congregacao_destino = models.ForeignKey(
        Congregacao,
        on_delete=models.PROTECT,
        related_name="discursos_recebidos",
        verbose_name="congregação de destino",
    )
    data = models.DateField()
    hora = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AGENDADO,
    )
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        ordering = ["data", "hora"]
        verbose_name = "discurso"
        verbose_name_plural = "discursos"

    def __str__(self):
        return f"{self.tema_para_exibicao} - {self.orador} ({self.data:%d/%m/%Y})"

    @property
    def tema_para_exibicao(self):
        if self.tema_predefinido:
            return str(self.tema_predefinido)
        return self.tema

    @property
    def tema_para_mensagem(self):
        if self.tema_predefinido:
            return self.tema_predefinido.titulo
        return self.tema

    @property
    def pode_notificar(self):
        return self.status in {self.Status.AGENDADO, self.Status.CONFIRMADO}

    def clean(self):
        if not self.tema_predefinido and not self.tema:
            raise ValidationError(
                {"tema_predefinido": "Informe um tema predefinido ou um tema manual."}
            )


class NotificacaoQuerySet(models.QuerySet):
    def pendentes(self, data_referencia=None):
        data_referencia = data_referencia or timezone.localdate()
        return self.filter(
            status_envio=Notificacao.StatusEnvio.PENDENTE,
            data_prevista__lte=data_referencia,
            discurso__status__in=[Discurso.Status.AGENDADO, Discurso.Status.CONFIRMADO],
            discurso__orador__ativo=True,
        )


class Notificacao(models.Model):
    class Marco(models.IntegerChoices):
        TRINTA = 30, "30 dias"
        QUINZE = 15, "15 dias"
        SETE = 7, "7 dias"
        DOIS = 2, "2 dias"

    class StatusEnvio(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ENVIADO = "enviado", "Enviado"
        ERRO = "erro", "Erro"

    discurso = models.ForeignKey(Discurso, on_delete=models.CASCADE, related_name="notificacoes")
    marco = models.PositiveSmallIntegerField(choices=Marco.choices)
    data_prevista = models.DateField()
    data_envio = models.DateTimeField(null=True, blank=True)
    status_envio = models.CharField(
        max_length=20,
        choices=StatusEnvio.choices,
        default=StatusEnvio.PENDENTE,
    )
    provedor = models.CharField(max_length=30, blank=True)
    telefone_destino = models.CharField(max_length=30, blank=True)
    message_id = models.CharField(max_length=100, blank=True, db_index=True)
    zaap_id = models.CharField(max_length=100, blank=True, db_index=True)
    status_whatsapp = models.CharField(max_length=30, blank=True)
    data_status_whatsapp = models.DateTimeField(null=True, blank=True)
    resposta_api = models.TextField(blank=True)

    objects = NotificacaoQuerySet.as_manager()

    class Meta:
        ordering = ["data_prevista", "discurso", "marco"]
        constraints = [
            models.UniqueConstraint(
                fields=["discurso", "marco"],
                name="notificacao_unica_por_discurso_marco",
            )
        ]
        verbose_name = "notificação"
        verbose_name_plural = "notificações"

    def __str__(self):
        return f"{self.discurso} - {self.marco} dias"

    def clean(self):
        if self.marco not in self.Marco.values:
            raise ValidationError({"marco": "Marco de notificação inválido."})


class RespostaNotificacao(models.Model):
    notificacao = models.ForeignKey(
        Notificacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respostas",
    )
    telefone = models.CharField(max_length=30)
    nome_contato = models.CharField(max_length=150, blank=True)
    mensagem = models.TextField(blank=True)
    message_id = models.CharField(max_length=100, blank=True, db_index=True)
    reference_message_id = models.CharField(max_length=100, blank=True, db_index=True)
    data_recebimento = models.DateTimeField(default=timezone.now)
    payload_api = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-data_recebimento", "-id"]
        verbose_name = "resposta de notificação"
        verbose_name_plural = "respostas de notificações"

    def __str__(self):
        alvo = self.notificacao or self.telefone
        return f"Resposta de {self.telefone} para {alvo}"


class EventoStatusMensagem(models.Model):
    notificacao = models.ForeignKey(
        Notificacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_status",
    )
    status = models.CharField(max_length=30)
    telefone = models.CharField(max_length=30, blank=True)
    message_id = models.CharField(max_length=100, blank=True, db_index=True)
    data_evento = models.DateTimeField(default=timezone.now)
    payload_api = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-data_evento", "-id"]
        verbose_name = "evento de status da mensagem"
        verbose_name_plural = "eventos de status das mensagens"

    def __str__(self):
        return f"{self.status} - {self.message_id or self.telefone}"
