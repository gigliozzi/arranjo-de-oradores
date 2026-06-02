from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("discursos", "0002_congregacao_endereco"),
    ]

    operations = [
        migrations.AddField(
            model_name="notificacao",
            name="data_status_whatsapp",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notificacao",
            name="message_id",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name="notificacao",
            name="provedor",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="notificacao",
            name="status_whatsapp",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="notificacao",
            name="telefone_destino",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name="notificacao",
            name="zaap_id",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.CreateModel(
            name="RespostaNotificacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telefone", models.CharField(max_length=30)),
                ("nome_contato", models.CharField(blank=True, max_length=150)),
                ("mensagem", models.TextField(blank=True)),
                ("message_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("reference_message_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("data_recebimento", models.DateTimeField(default=django.utils.timezone.now)),
                ("payload_api", models.JSONField(blank=True, default=dict)),
                (
                    "notificacao",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="respostas",
                        to="discursos.notificacao",
                    ),
                ),
            ],
            options={
                "verbose_name": "resposta de notificação",
                "verbose_name_plural": "respostas de notificações",
                "ordering": ["-data_recebimento", "-id"],
            },
        ),
        migrations.CreateModel(
            name="EventoStatusMensagem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(max_length=30)),
                ("telefone", models.CharField(blank=True, max_length=30)),
                ("message_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("data_evento", models.DateTimeField(default=django.utils.timezone.now)),
                ("payload_api", models.JSONField(blank=True, default=dict)),
                (
                    "notificacao",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="eventos_status",
                        to="discursos.notificacao",
                    ),
                ),
            ],
            options={
                "verbose_name": "evento de status da mensagem",
                "verbose_name_plural": "eventos de status das mensagens",
                "ordering": ["-data_evento", "-id"],
            },
        ),
    ]
