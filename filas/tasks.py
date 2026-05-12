from django.utils import timezone
from .models import Atendimento


def resetar_filas():
    """Deleta atendimentos de dias anteriores. Roda todo dia à meia-noite."""
    hoje = timezone.now().date()
    deletados, _ = Atendimento.objects.filter(criado_em__date__lt=hoje).delete()
    print(f"[CeciFácil] Reset: {deletados} atendimentos removidos.")
