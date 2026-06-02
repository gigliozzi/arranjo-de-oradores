import csv
from pathlib import Path

from django.db import migrations


def carregar_temas_discursos(apps, schema_editor):
    TemaDiscurso = apps.get_model("discursos", "TemaDiscurso")
    caminho = Path(__file__).resolve().parents[1] / "data" / "esbocos-discursos.CSV"

    if not caminho.exists():
        return

    conteudo = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            conteudo = caminho.read_text(encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    if conteudo is None:
        return

    linhas = conteudo.splitlines()
    reader = csv.DictReader(linhas, delimiter=";")

    for row in reader:
        numero = int((row.get("numero") or "").strip())
        titulo = (row.get("titulo") or "").strip()
        ativo_raw = (row.get("ativo") or "true").strip().lower()
        ativo = ativo_raw in {"true", "1", "sim", "s", "ativo"}

        if not titulo:
            continue

        TemaDiscurso.objects.update_or_create(
            numero=numero,
            defaults={"titulo": titulo, "ativo": ativo},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("discursos", "0004_temadiscurso_alter_discurso_tema_and_more"),
    ]

    operations = [
        migrations.RunPython(carregar_temas_discursos, migrations.RunPython.noop),
    ]
