import csv
import io
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from discursos.models import TemaDiscurso


class Command(BaseCommand):
    help = "Importa temas de discursos a partir de CSV/TXT."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho do arquivo CSV/TXT com numero, titulo e ativo.")
        parser.add_argument(
            "--desativar-ausentes",
            action="store_true",
            help="Marca como inativos os temas já cadastrados que não aparecem no arquivo.",
        )

    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo não encontrado: {caminho}")

        linhas = self._ler_linhas(caminho)
        criados = 0
        atualizados = 0
        numeros_importados = set()

        with transaction.atomic():
            for indice, row in enumerate(self._iterar_csv(linhas), start=2):
                dados = self._normalizar_linha(row)
                numero = self._parse_numero(dados.get("numero"), indice)
                titulo = (dados.get("titulo") or "").strip()
                ativo = self._parse_ativo(dados.get("ativo"))

                if not titulo:
                    raise CommandError(f"Linha {indice}: título não informado.")

                tema, created = TemaDiscurso.objects.update_or_create(
                    numero=numero,
                    defaults={"titulo": titulo, "ativo": ativo},
                )
                numeros_importados.add(tema.numero)
                if created:
                    criados += 1
                else:
                    atualizados += 1

            desativados = 0
            if options["desativar_ausentes"]:
                desativados = (
                    TemaDiscurso.objects.exclude(numero__in=numeros_importados)
                    .filter(ativo=True)
                    .update(ativo=False)
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Temas importados: "
                f"{criados} criados, {atualizados} atualizados, {desativados} desativados."
            )
        )

    def _ler_linhas(self, caminho):
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return caminho.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise CommandError("Não foi possível ler o arquivo. Verifique a codificação.")

    def _iterar_csv(self, conteudo):
        amostra = conteudo[:2048]
        try:
            delimiter = csv.Sniffer().sniff(amostra, delimiters=";,").delimiter
        except csv.Error:
            delimiter = ";"

        reader = csv.DictReader(io.StringIO(conteudo), delimiter=delimiter)
        if not reader.fieldnames:
            raise CommandError("Arquivo sem cabeçalho. Use as colunas: numero, titulo, ativo.")

        campos = {self._normalizar_chave(campo) for campo in reader.fieldnames}
        obrigatorios = {"numero", "titulo"}
        if not obrigatorios.issubset(campos):
            raise CommandError("Cabeçalho inválido. Use as colunas: numero, titulo, ativo.")

        return reader

    def _normalizar_linha(self, row):
        return {self._normalizar_chave(chave): valor for chave, valor in row.items()}

    def _normalizar_chave(self, chave):
        return (chave or "").strip().lower().replace("\ufeff", "")

    def _parse_numero(self, valor, indice):
        try:
            numero = int(str(valor).strip())
        except (TypeError, ValueError) as exc:
            raise CommandError(f"Linha {indice}: número inválido.") from exc
        if numero < 1:
            raise CommandError(f"Linha {indice}: número deve ser maior que zero.")
        return numero

    def _parse_ativo(self, valor):
        if valor is None or str(valor).strip() == "":
            return True
        normalizado = str(valor).strip().lower()
        if normalizado in {"true", "1", "sim", "s", "ativo"}:
            return True
        if normalizado in {"false", "0", "nao", "não", "n", "inativo"}:
            return False
        raise CommandError(f"Valor inválido para ativo: {valor}")
