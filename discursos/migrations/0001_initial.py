# Generated manually for the initial Arranjo de Oradores schema.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Congregacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                ("cidade", models.CharField(max_length=100)),
                ("estado", models.CharField(max_length=2)),
                ("responsavel", models.CharField(blank=True, max_length=150, verbose_name="responsável")),
                ("telefone", models.CharField(blank=True, max_length=30)),
            ],
            options={
                "verbose_name": "congregação",
                "verbose_name_plural": "congregações",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Orador",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                ("celular", models.CharField(max_length=30)),
                ("congregacao_origem", models.CharField(max_length=150, verbose_name="congregação de origem")),
                ("observacoes", models.TextField(blank=True, verbose_name="observações")),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "orador",
                "verbose_name_plural": "oradores",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Discurso",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tema", models.CharField(max_length=200)),
                ("data", models.DateField()),
                ("hora", models.TimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("agendado", "Agendado"),
                            ("confirmado", "Confirmado"),
                            ("cancelado", "Cancelado"),
                            ("realizado", "Realizado"),
                        ],
                        default="agendado",
                        max_length=20,
                    ),
                ),
                ("observacoes", models.TextField(blank=True, verbose_name="observações")),
                (
                    "congregacao_destino",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="discursos_recebidos",
                        to="discursos.congregacao",
                        verbose_name="congregação de destino",
                    ),
                ),
                (
                    "orador",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="discursos",
                        to="discursos.orador",
                    ),
                ),
            ],
            options={
                "verbose_name": "discurso",
                "verbose_name_plural": "discursos",
                "ordering": ["data", "hora"],
            },
        ),
        migrations.CreateModel(
            name="Notificacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("marco", models.PositiveSmallIntegerField(choices=[(30, "30 dias"), (15, "15 dias"), (7, "7 dias"), (2, "2 dias")])),
                ("data_prevista", models.DateField()),
                ("data_envio", models.DateTimeField(blank=True, null=True)),
                (
                    "status_envio",
                    models.CharField(
                        choices=[("pendente", "Pendente"), ("enviado", "Enviado"), ("erro", "Erro")],
                        default="pendente",
                        max_length=20,
                    ),
                ),
                ("resposta_api", models.TextField(blank=True)),
                (
                    "discurso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notificacoes",
                        to="discursos.discurso",
                    ),
                ),
            ],
            options={
                "verbose_name": "notificação",
                "verbose_name_plural": "notificações",
                "ordering": ["data_prevista", "discurso", "marco"],
            },
        ),
        migrations.AddConstraint(
            model_name="notificacao",
            constraint=models.UniqueConstraint(fields=("discurso", "marco"), name="notificacao_unica_por_discurso_marco"),
        ),
    ]
