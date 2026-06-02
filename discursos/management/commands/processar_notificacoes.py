from django.core.management.base import BaseCommand

from discursos.models import Notificacao
from discursos.services import processar_notificacoes_pendentes


class Command(BaseCommand):
    help = "Processa notificações pendentes de discursos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista as notificações que seriam processadas, sem enviar mensagens.",
        )
        parser.add_argument(
            "--limite",
            type=int,
            help="Limita a quantidade de notificações processadas.",
        )
        parser.add_argument(
            "--notificacao-id",
            type=int,
            help="Processa uma notificação específica pelo ID.",
        )

    def handle(self, *args, **options):
        limite = options.get("limite")
        if limite is not None and limite < 1:
            self.stderr.write(self.style.ERROR("--limite deve ser maior que zero."))
            return

        resultado = processar_notificacoes_pendentes(
            notificacao_id=options.get("notificacao_id"),
            limite=limite,
            dry_run=options["dry_run"],
        )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY-RUN: nenhuma mensagem foi enviada."))
            self._escrever_notificacoes(resultado["notificacoes"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Notificações encontradas: {resultado['pendentes']}."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Notificações processadas: "
                f"{resultado['pendentes']} pendentes, "
                f"{resultado['enviadas']} enviadas, "
                f"{resultado['erros']} erros."
            )
        )

    def _escrever_notificacoes(self, notificacoes):
        for notificacao in notificacoes:
            status = (
                "reenviar"
                if notificacao.status_envio == Notificacao.StatusEnvio.ERRO
                else notificacao.status_envio
            )
            self.stdout.write(
                f"#{notificacao.id} | {status} | marco {notificacao.marco} dias | "
                f"{notificacao.discurso.data:%d/%m/%Y} | "
                f"{notificacao.discurso.orador.nome} | "
                f"{notificacao.discurso.congregacao_destino.nome}"
            )
