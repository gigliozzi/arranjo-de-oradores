import json
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    Congregacao,
    Discurso,
    EventoStatusMensagem,
    Notificacao,
    RespostaNotificacao,
)

MARCOS_NOTIFICACAO = (30, 15, 7, 2)


def criar_notificacoes_para_discurso(discurso):
    notificacoes = []
    data_cadastro = timezone.localtime(discurso.criado_em).date() if discurso.criado_em else None
    for marco in MARCOS_NOTIFICACAO:
        data_prevista = discurso.data - timedelta(days=marco)
        if data_cadastro and data_prevista < data_cadastro:
            Notificacao.objects.filter(discurso=discurso, marco=marco).exclude(
                status_envio=Notificacao.StatusEnvio.ENVIADO
            ).delete()
            continue

        notificacao, created = Notificacao.objects.get_or_create(
            discurso=discurso,
            marco=marco,
            defaults={"data_prevista": data_prevista},
        )
        if not created and notificacao.status_envio != Notificacao.StatusEnvio.ENVIADO:
            notificacao.data_prevista = data_prevista
            notificacao.save(update_fields=["data_prevista"])
        notificacoes.append(notificacao)
    return notificacoes


def sincronizar_notificacoes_agendadas():
    discursos = Discurso.objects.filter(
        status__in=[Discurso.Status.AGENDADO, Discurso.Status.CONFIRMADO],
        orador__ativo=True,
    )
    total = 0
    for discurso in discursos:
        total += len(criar_notificacoes_para_discurso(discurso))
    return total


def identificar_notificacoes_pendentes(data_referencia=None):
    return Notificacao.objects.pendentes(
        data_referencia=data_referencia
    ).select_related(
        "discurso",
        "discurso__tema_predefinido",
        "discurso__orador",
        "discurso__congregacao_destino",
    )


def enviar_whatsapp_simulado(notificacao):
    mensagem = montar_mensagem_whatsapp(notificacao)
    return {
        "provider": "simulado",
        "message": f"Simulação WhatsApp: {mensagem}",
        "phone": normalizar_celular(notificacao.discurso.orador.celular),
    }


def montar_mensagem_whatsapp(notificacao):
    discurso = notificacao.discurso
    endereco = discurso.congregacao_destino.endereco_formatado
    endereco_linha = f"Endereço: {endereco}. \n" if endereco else ""
    return (
        f"Olá, irmão *{discurso.orador.nome}*. \n\n"
        f"Este é um lembrete automático do seu discurso que ocorrerá em {notificacao.marco} dias. \n\n"
        f"Tema: {discurso.tema_para_mensagem} \n"
        f"Congregação: {discurso.congregacao_destino.nome} \n"
        f"{endereco_linha}"
        f"Data: {discurso.data:%d/%m/%Y} às {discurso.hora:%H:%M} \n\n"
        f"Em caso de imprevistos, por favor, entre em contato com o irmão Sebastião Paulo."
    )


def normalizar_celular(celular):
    return re.sub(r"\D", "", celular or "")


def normalizar_cep(cep):
    return re.sub(r"\D", "", cep or "")


def buscar_endereco_por_cep(cep):
    cep_normalizado = normalizar_cep(cep)
    if len(cep_normalizado) != 8:
        raise ValueError("CEP deve conter 8 dígitos.")

    response = requests.get(
        f"https://viacep.com.br/ws/{cep_normalizado}/json/",
        timeout=10,
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise ValueError("ViaCEP retornou uma resposta inválida.") from exc

    if response.status_code >= 400:
        raise ValueError(f"ViaCEP retornou HTTP {response.status_code}.")
    if body.get("erro"):
        raise ValueError("CEP não encontrado no ViaCEP.")

    return {
        "cep": body.get("cep", ""),
        "logradouro": body.get("logradouro", ""),
        "complemento": body.get("complemento", ""),
        "bairro": body.get("bairro", ""),
        "cidade": body.get("localidade", ""),
        "estado": body.get("uf", ""),
    }


def preencher_endereco_por_cep(congregacao):
    if not congregacao.cep:
        return congregacao

    endereco = buscar_endereco_por_cep(congregacao.cep)
    for campo, valor in endereco.items():
        if campo == "complemento":
            continue
        if valor and not getattr(congregacao, campo):
            setattr(congregacao, campo, valor)
    return congregacao


def enviar_whatsapp_zapi(notificacao):
    validar_configuracao_zapi()

    telefone = normalizar_celular(notificacao.discurso.orador.celular)
    if not telefone:
        raise ValueError("Celular do orador não informado.")

    url = montar_url_zapi_send_text()
    payload = {
        "phone": telefone,
        "message": montar_mensagem_whatsapp(notificacao),
    }
    headers = {
        "Client-Token": settings.ZAPI_CLIENT_TOKEN,
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=settings.ZAPI_TIMEOUT_SECONDS,
    )
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}

    if response.status_code >= 400:
        raise ValueError(
            f"Z-API retornou HTTP {response.status_code}: {json.dumps(body, ensure_ascii=False)}"
        )
    if isinstance(body, dict) and body.get("error"):
        raise ValueError(f"Z-API retornou erro: {json.dumps(body, ensure_ascii=False)}")
    if not isinstance(body, dict) or not any(
        body.get(campo) for campo in ("messageId", "id", "zaapId")
    ):
        raise ValueError(
            f"Resposta inesperada da Z-API: {json.dumps(body, ensure_ascii=False)}"
        )

    return {
        "provider": "z-api",
        "message": json.dumps(body, ensure_ascii=False),
        "phone": telefone,
        "message_id": body.get("messageId") or body.get("id", ""),
        "zaap_id": body.get("zaapId", ""),
    }


def montar_url_zapi_send_text():
    base_url = settings.ZAPI_BASE_URL.rstrip("/")
    if base_url.endswith("/send-text"):
        return base_url
    return (
        f"{base_url}/instances/"
        f"{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_INSTANCE_TOKEN}/send-text"
    )


def validar_configuracao_zapi():
    campos = {
        "ZAPI_INSTANCE_ID": settings.ZAPI_INSTANCE_ID,
        "ZAPI_INSTANCE_TOKEN": settings.ZAPI_INSTANCE_TOKEN,
        "ZAPI_CLIENT_TOKEN": settings.ZAPI_CLIENT_TOKEN,
    }
    faltando = [nome for nome, valor in campos.items() if not valor]
    if faltando:
        raise ValueError(f"Configuração Z-API incompleta: {', '.join(faltando)}.")


def enviar_whatsapp(notificacao):
    if settings.ZAPI_ENABLED:
        return enviar_whatsapp_zapi(notificacao)
    return enviar_whatsapp_simulado(notificacao)


@transaction.atomic
def processar_notificacao(notificacao):
    notificacao = (
        Notificacao.objects.select_for_update(of=("self",))
        .select_related(
            "discurso",
            "discurso__tema_predefinido",
            "discurso__orador",
            "discurso__congregacao_destino",
        )
        .get(pk=notificacao.pk)
    )
    if notificacao.status_envio == Notificacao.StatusEnvio.ENVIADO:
        return notificacao

    try:
        resposta = enviar_whatsapp(notificacao)
    except Exception as exc:
        notificacao.status_envio = Notificacao.StatusEnvio.ERRO
        notificacao.resposta_api = str(exc)
    else:
        notificacao.status_envio = Notificacao.StatusEnvio.ENVIADO
        notificacao.data_envio = timezone.now()
        notificacao.resposta_api = resposta["message"]
        notificacao.provedor = resposta.get("provider", "")
        notificacao.telefone_destino = resposta.get("phone", "")
        notificacao.message_id = resposta.get("message_id", "")
        notificacao.zaap_id = resposta.get("zaap_id", "")
    notificacao.save(
        update_fields=[
            "status_envio",
            "data_envio",
            "resposta_api",
            "provedor",
            "telefone_destino",
            "message_id",
            "zaap_id",
        ]
    )
    return notificacao


def listar_notificacoes_para_processamento(
    data_referencia=None, notificacao_id=None, limite=None
):
    sincronizar_notificacoes_agendadas()
    if notificacao_id:
        queryset = Notificacao.objects.filter(pk=notificacao_id).select_related(
            "discurso",
            "discurso__tema_predefinido",
            "discurso__orador",
            "discurso__congregacao_destino",
        )
    else:
        queryset = identificar_notificacoes_pendentes(data_referencia=data_referencia)

    queryset = queryset.order_by("data_prevista", "id")
    if limite:
        queryset = queryset[:limite]
    return list(queryset)


def processar_notificacoes_pendentes(
    data_referencia=None, notificacao_id=None, limite=None, dry_run=False
):
    notificacoes = listar_notificacoes_para_processamento(
        data_referencia=data_referencia,
        notificacao_id=notificacao_id,
        limite=limite,
    )
    if dry_run:
        return {
            "pendentes": len(notificacoes),
            "enviadas": 0,
            "erros": 0,
            "dry_run": True,
            "notificacoes": notificacoes,
        }

    enviadas = 0
    erros = 0
    for notificacao in notificacoes:
        resultado = processar_notificacao(notificacao)
        if resultado.status_envio == Notificacao.StatusEnvio.ENVIADO:
            enviadas += 1
        elif resultado.status_envio == Notificacao.StatusEnvio.ERRO:
            erros += 1
    return {
        "pendentes": len(notificacoes),
        "enviadas": enviadas,
        "erros": erros,
        "dry_run": False,
        "notificacoes": notificacoes,
    }


def timestamp_zapi_para_datetime(valor):
    if not valor:
        return timezone.now()
    try:
        timestamp = int(valor)
    except (TypeError, ValueError):
        return timezone.now()
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    return timezone.datetime.fromtimestamp(
        timestamp, tz=timezone.get_current_timezone()
    )


def extrair_texto_payload_recebido(payload):
    texto = payload.get("text")
    if isinstance(texto, dict):
        return texto.get("message", "") or texto.get("description", "")
    if isinstance(texto, str):
        return texto
    return payload.get("message", "") or payload.get("body", "")


def encontrar_notificacao_por_resposta(payload):
    reference_message_id = (
        payload.get("referenceMessageId") or payload.get("quotedMsgId") or ""
    )
    if reference_message_id:
        notificacao = Notificacao.objects.filter(
            message_id=reference_message_id
        ).first()
        if notificacao:
            return notificacao

    telefone = normalizar_celular(payload.get("phone", ""))
    if not telefone:
        return None

    return (
        Notificacao.objects.filter(
            telefone_destino=telefone,
            status_envio=Notificacao.StatusEnvio.ENVIADO,
        )
        .order_by("-data_envio", "-id")
        .first()
    )


def registrar_resposta_notificacao(payload):
    if payload.get("fromMe") or payload.get("isGroup") or payload.get("isNewsletter"):
        return None

    notificacao = encontrar_notificacao_por_resposta(payload)
    resposta = RespostaNotificacao.objects.create(
        notificacao=notificacao,
        telefone=normalizar_celular(payload.get("phone", "")),
        nome_contato=payload.get("senderName", "") or payload.get("chatName", ""),
        mensagem=extrair_texto_payload_recebido(payload),
        message_id=payload.get("messageId", ""),
        reference_message_id=payload.get("referenceMessageId", "")
        or payload.get("quotedMsgId", ""),
        data_recebimento=timestamp_zapi_para_datetime(payload.get("momment")),
        payload_api=payload,
    )
    return resposta


def registrar_status_mensagem(payload):
    ids = payload.get("ids") or []
    if isinstance(ids, str):
        ids = [ids]

    eventos = []
    for message_id in ids:
        notificacao = Notificacao.objects.filter(message_id=message_id).first()
        evento = EventoStatusMensagem.objects.create(
            notificacao=notificacao,
            status=payload.get("status", ""),
            telefone=normalizar_celular(payload.get("phone", "")),
            message_id=message_id,
            data_evento=timestamp_zapi_para_datetime(payload.get("momment")),
            payload_api=payload,
        )
        eventos.append(evento)

        if notificacao:
            notificacao.status_whatsapp = evento.status
            notificacao.data_status_whatsapp = evento.data_evento
            notificacao.save(update_fields=["status_whatsapp", "data_status_whatsapp"])

    return eventos
