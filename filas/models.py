import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UPA(models.Model):
    nome      = models.CharField(max_length=100)
    slug      = models.SlugField(unique=True)
    ativo     = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'UPA'
        verbose_name_plural = 'UPAs'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class PerfilDiretor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_diretor')
    upa     = models.ForeignKey(UPA, on_delete=models.CASCADE, related_name='diretores')

    class Meta:
        verbose_name = 'Diretor'
        verbose_name_plural = 'Diretores'

    def __str__(self):
        return f"{self.usuario.username} — {self.upa.nome} (Diretor)"


class PerfilRecepcionista(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    upa     = models.ForeignKey(UPA, on_delete=models.CASCADE, related_name='recepcionistas')

    class Meta:
        verbose_name = 'Recepcionista'
        verbose_name_plural = 'Recepcionistas'

    def __str__(self):
        return f"{self.usuario.username} — {self.upa.nome}"


class Atendimento(models.Model):

    TIPOS = [
        ('consulta', 'Consulta'),
        ('vacina',   'Vacina'),
        ('curativo', 'Curativo'),
        ('farmacia', 'Farmácia'),
    ]

    STATUS = [
        ('aguardando',     'Aguardando'),
        ('chamado',        'Chamado'),
        ('nao_compareceu', 'Não compareceu'),
        ('atendido',       'Atendido'),
        ('ausente',        'Ausente'),
    ]

    PREFIXOS = {
        'consulta': 'CON',
        'vacina':   'VAC',
        'curativo': 'CUR',
        'farmacia': 'FAR',
    }

    MOTIVOS_PRIORIDADE = [
        ('idoso',       'Idoso (60+)'),
        ('gestante',    'Gestante'),
        ('deficiencia', 'Pessoa com deficiência'),
        ('crianca',     'Criança (menor de 5 anos)'),
        ('outro',       'Outro'),
    ]

    ORIGENS = [
        ('online',     'Online'),
        ('presencial', 'Presencial'),
    ]

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upa               = models.ForeignKey(UPA, on_delete=models.CASCADE, related_name='atendimentos')
    nome              = models.CharField(max_length=100)
    tipo              = models.CharField(max_length=20, choices=TIPOS)
    origem            = models.CharField(max_length=10, choices=ORIGENS, default='online')
    prioridade        = models.BooleanField(default=False)
    motivo_prioridade = models.CharField(max_length=20, choices=MOTIVOS_PRIORIDADE, blank=True)
    senha             = models.CharField(max_length=10, blank=True)
    status            = models.CharField(max_length=20, choices=STATUS, default='aguardando')
    criado_em         = models.DateTimeField(auto_now_add=True)
    chamado_em        = models.DateTimeField(null=True, blank=True)
    atendido_em       = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-prioridade', 'criado_em']
        verbose_name = 'Atendimento'
        verbose_name_plural = 'Atendimentos'

    def __str__(self):
        return f"{self.senha} — {self.nome} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.senha:
            self.senha = self._gerar_senha()
        super().save(*args, **kwargs)

    def _gerar_senha(self):
        hoje = timezone.now().date()
        prefixo = self.PREFIXOS.get(self.tipo, 'ATD')

        ultimo = Atendimento.objects.filter(
            upa=self.upa,
            tipo=self.tipo,
            criado_em__date=hoje
        ).order_by('criado_em').last()

        numero = 1
        if ultimo and ultimo.senha:
            try:
                numero = int(ultimo.senha.split('-')[1]) + 1
            except (IndexError, ValueError):
                numero = 1

        return f"{prefixo}-{numero:03d}"

    def posicao_na_fila(self):
        return Atendimento.objects.filter(
            upa=self.upa,
            tipo=self.tipo,
            status='aguardando',
            criado_em__lte=self.criado_em
        ).count()

    def chamar(self):
        self.status = 'chamado'
        self.chamado_em = timezone.now()
        self.save()

    def atender(self):
        self.status = 'atendido'
        self.atendido_em = timezone.now()
        self.save()

    def nao_compareceu(self):
        self.status = 'nao_compareceu'
        self.save()

    def marcar_ausente(self):
        self.status = 'ausente'
        self.save()

    def reconvocar(self):
        self.status = 'aguardando'
        self.chamado_em = None
        self.save()
