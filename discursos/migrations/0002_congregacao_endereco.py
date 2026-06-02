from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("discursos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="congregacao",
            name="bairro",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="congregacao",
            name="cep",
            field=models.CharField(blank=True, max_length=9, verbose_name="CEP"),
        ),
        migrations.AddField(
            model_name="congregacao",
            name="complemento",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="congregacao",
            name="logradouro",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="congregacao",
            name="numero",
            field=models.CharField(blank=True, max_length=20, verbose_name="número"),
        ),
        migrations.AlterField(
            model_name="congregacao",
            name="cidade",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="congregacao",
            name="estado",
            field=models.CharField(blank=True, max_length=2),
        ),
    ]
