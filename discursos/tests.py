from datetime import time, timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.test import TestCase
from django.utils import timezone

from .models import Congregacao, Discurso, Notificacao, Orador
from .services import (
    buscar_endereco_por_cep,
    criar_notificacoes_para_discurso,
    enviar_whatsapp_zapi,
    montar_mensagem_whatsapp,
    montar_url_zapi_send_text,
    preencher_endereco_por_cep,
    processar_notificacoes_pendentes,
)


class NotificacaoTests(TestCase):
    def setUp(self):
        self.orador = Orador.objects.create(
            nome="João Silva",
            celular="5511999999999",
            congregacao_origem="Central",
        )
        self.congregacao = Congregacao.objects.create(
            nome="Jardim",
            cidade="São Paulo",
            estado="SP",
            cep="01001-000",
            logradouro="Praça da Sé",
            numero="10",
            bairro="Sé",
            responsavel="Carlos",
            telefone="5511888888888",
        )

    def criar_discurso(self, dias=30):
        return Discurso.objects.create(
            orador=self.orador,
            tema="Confie em Jeová",
            congregacao_destino=self.congregacao,
            data=timezone.localdate() + timedelta(days=dias),
            hora=time(19, 30),
            status=Discurso.Status.AGENDADO,
        )

    def test_cria_quatro_notificacoes_por_discurso(self):
        discurso = self.criar_discurso()

        criar_notificacoes_para_discurso(discurso)

        self.assertEqual(discurso.notificacoes.count(), 4)
        self.assertEqual(
            set(discurso.notificacoes.values_list("marco", flat=True)),
            {30, 15, 7, 2},
        )

    def test_nao_duplica_mesmo_marco_para_o_mesmo_discurso(self):
        discurso = self.criar_discurso()

        criar_notificacoes_para_discurso(discurso)
        criar_notificacoes_para_discurso(discurso)

        self.assertEqual(discurso.notificacoes.count(), 4)

    @override_settings(ZAPI_ENABLED=False)
    def test_processa_notificacoes_pendentes_com_envio_simulado(self):
        discurso = self.criar_discurso(dias=2)

        resultado = processar_notificacoes_pendentes()

        self.assertEqual(resultado["erros"], 0)
        self.assertEqual(resultado["enviadas"], 4)
        self.assertEqual(
            Notificacao.objects.filter(
                discurso=discurso,
                status_envio=Notificacao.StatusEnvio.ENVIADO,
                data_envio__isnull=False,
            ).count(),
            4,
        )

    @override_settings(ZAPI_ENABLED=False)
    def test_dry_run_nao_altera_notificacoes(self):
        discurso = self.criar_discurso(dias=2)

        resultado = processar_notificacoes_pendentes(dry_run=True)

        self.assertTrue(resultado["dry_run"])
        self.assertEqual(resultado["pendentes"], 4)
        self.assertEqual(
            Notificacao.objects.filter(
                discurso=discurso,
                status_envio=Notificacao.StatusEnvio.PENDENTE,
            ).count(),
            4,
        )

    @override_settings(ZAPI_ENABLED=False)
    def test_limite_processa_apenas_quantidade_informada(self):
        discurso = self.criar_discurso(dias=2)

        resultado = processar_notificacoes_pendentes(limite=1)

        self.assertEqual(resultado["pendentes"], 1)
        self.assertEqual(resultado["enviadas"], 1)
        self.assertEqual(
            Notificacao.objects.filter(
                discurso=discurso,
                status_envio=Notificacao.StatusEnvio.ENVIADO,
            ).count(),
            1,
        )

    @override_settings(ZAPI_ENABLED=False)
    def test_notificacao_id_processa_registro_especifico(self):
        discurso = self.criar_discurso(dias=2)
        notificacao = discurso.notificacoes.get(marco=7)

        resultado = processar_notificacoes_pendentes(notificacao_id=notificacao.id)

        notificacao.refresh_from_db()
        self.assertEqual(resultado["pendentes"], 1)
        self.assertEqual(notificacao.status_envio, Notificacao.StatusEnvio.ENVIADO)

    @override_settings(
        ZAPI_BASE_URL="https://api.z-api.io",
        ZAPI_INSTANCE_ID="instancia",
        ZAPI_INSTANCE_TOKEN="token",
        ZAPI_CLIENT_TOKEN="client-token",
        ZAPI_TIMEOUT_SECONDS=15,
    )
    @patch("discursos.services.requests.post")
    def test_envio_zapi_monta_requisicao_sem_chamar_api_real(self, post):
        discurso = self.criar_discurso()
        notificacao = discurso.notificacoes.get(marco=30)
        response = Mock(status_code=200)
        response.json.return_value = {"messageId": "abc123"}
        post.return_value = response

        resultado = enviar_whatsapp_zapi(notificacao)

        post.assert_called_once()
        _, kwargs = post.call_args
        self.assertEqual(kwargs["json"]["phone"], "5511999999999")
        self.assertIn("Confie em Jeová", kwargs["json"]["message"])
        self.assertEqual(kwargs["headers"]["Client-Token"], "client-token")
        self.assertEqual(resultado["provider"], "z-api")

    @override_settings(
        ZAPI_BASE_URL="https://api.z-api.io",
        ZAPI_INSTANCE_ID="instancia",
        ZAPI_INSTANCE_TOKEN="token",
        ZAPI_CLIENT_TOKEN="client-token",
        ZAPI_TIMEOUT_SECONDS=15,
    )
    @patch("discursos.services.requests.post")
    def test_envio_zapi_rejeita_resposta_com_error(self, post):
        discurso = self.criar_discurso()
        notificacao = discurso.notificacoes.get(marco=30)
        response = Mock(status_code=200)
        response.json.return_value = {
            "error": "NOT_FOUND",
            "message": "Unable to find matching target resource method",
        }
        post.return_value = response

        with self.assertRaisesMessage(ValueError, "Z-API retornou erro"):
            enviar_whatsapp_zapi(notificacao)

    @override_settings(
        ZAPI_BASE_URL="https://api.z-api.io/instances/instancia/token/token/send-text",
        ZAPI_INSTANCE_ID="instancia",
        ZAPI_INSTANCE_TOKEN="token",
    )
    def test_montar_url_zapi_aceita_endpoint_completo(self):
        self.assertEqual(
            montar_url_zapi_send_text(),
            "https://api.z-api.io/instances/instancia/token/token/send-text",
        )

    def test_mensagem_whatsapp_inclui_endereco_da_congregacao(self):
        discurso = self.criar_discurso()
        notificacao = discurso.notificacoes.get(marco=30)

        mensagem = montar_mensagem_whatsapp(notificacao)

        self.assertIn("Endereço:", mensagem)
        self.assertIn("Praça da Sé, 10", mensagem)
        self.assertIn("CEP 01001-000", mensagem)

    @patch("discursos.services.requests.get")
    def test_buscar_endereco_por_cep_usa_viacep(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {
            "cep": "01001-000",
            "logradouro": "Praça da Sé",
            "complemento": "lado ímpar",
            "bairro": "Sé",
            "localidade": "São Paulo",
            "uf": "SP",
        }
        get.return_value = response

        endereco = buscar_endereco_por_cep("01001-000")

        self.assertEqual(endereco["logradouro"], "Praça da Sé")
        self.assertEqual(endereco["cidade"], "São Paulo")
        get.assert_called_once_with("https://viacep.com.br/ws/01001000/json/", timeout=10)

    @patch("discursos.services.buscar_endereco_por_cep")
    def test_preencher_endereco_por_cep_preserva_campos_preenchidos(self, buscar):
        buscar.return_value = {
            "cep": "01001-000",
            "logradouro": "Praça da Sé",
            "complemento": "lado ímpar",
            "bairro": "Sé",
            "cidade": "São Paulo",
            "estado": "SP",
        }
        congregacao = Congregacao(nome="Centro", cep="01001-000", numero="123")

        preencher_endereco_por_cep(congregacao)

        self.assertEqual(congregacao.logradouro, "Praça da Sé")
        self.assertEqual(congregacao.numero, "123")
        self.assertEqual(congregacao.bairro, "Sé")
