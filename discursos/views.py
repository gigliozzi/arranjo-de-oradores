import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import registrar_resposta_notificacao, registrar_status_mensagem


def webhook_autorizado(request):
    segredo = settings.ZAPI_WEBHOOK_SECRET
    if not segredo:
        return True
    recebido = request.GET.get("token") or request.headers.get("X-Webhook-Token")
    return recebido == segredo


def carregar_payload_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None


@csrf_exempt
@require_POST
def webhook_zapi_recebidas(request):
    if not webhook_autorizado(request):
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)

    payload = carregar_payload_json(request)
    if payload is None:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    resposta = registrar_resposta_notificacao(payload)
    return JsonResponse({"ok": True, "resposta_id": resposta.id if resposta else None})


@csrf_exempt
@require_POST
def webhook_zapi_status(request):
    if not webhook_autorizado(request):
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)

    payload = carregar_payload_json(request)
    if payload is None:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    eventos = registrar_status_mensagem(payload)
    return JsonResponse({"ok": True, "eventos": len(eventos)})
