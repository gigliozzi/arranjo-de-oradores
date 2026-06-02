from apscheduler.schedulers.blocking import BlockingScheduler
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Inicia o APScheduler para verificar notificações diariamente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hora",
            default="08:00",
            help="Horário diário de execução no formato HH:MM. Padrão: 08:00.",
        )

    def handle(self, *args, **options):
        hora, minuto = self._parse_hora(options["hora"])
        scheduler = BlockingScheduler(timezone=str(timezone.get_current_timezone()))

        scheduler.add_job(
            lambda: call_command("processar_notificacoes"),
            trigger="cron",
            hour=hora,
            minute=minuto,
            id="processar_notificacoes_diarias",
            replace_existing=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Agendador iniciado. Verificação diária configurada para {hora:02d}:{minuto:02d}."
            )
        )
        scheduler.start()

    def _parse_hora(self, valor):
        try:
            hora, minuto = [int(parte) for parte in valor.split(":", maxsplit=1)]
        except ValueError as exc:
            raise ValueError("Use o formato HH:MM para --hora.") from exc

        if not 0 <= hora <= 23 or not 0 <= minuto <= 59:
            raise ValueError("Horário inválido. Use HH entre 00-23 e MM entre 00-59.")
        return hora, minuto
