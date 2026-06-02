from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from discursos import views as discursos_views


def healthcheck(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    path("admin/", admin.site.urls),
    path("webhooks/zapi/recebidas/", discursos_views.webhook_zapi_recebidas, name="webhook_zapi_recebidas"),
    path("webhooks/zapi/status/", discursos_views.webhook_zapi_status, name="webhook_zapi_status"),
]
