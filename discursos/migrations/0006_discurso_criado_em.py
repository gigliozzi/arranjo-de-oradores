from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discursos', '0005_carregar_temas_discursos'),
    ]

    operations = [
        migrations.AddField(
            model_name='discurso',
            name='criado_em',
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='criado em'),
        ),
    ]
