from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Discurso
from .services import criar_notificacoes_para_discurso


@receiver(post_save, sender=Discurso)
def criar_notificacoes_ao_salvar_discurso(sender, instance, **kwargs):
    if instance.pode_notificar:
        criar_notificacoes_para_discurso(instance)
