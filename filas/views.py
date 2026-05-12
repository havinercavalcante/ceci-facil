from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.db.models import Avg, Count, ExpressionWrapper, F, DurationField
from django.db.models.functions import TruncDay, ExtractHour
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import UPA, Atendimento


# ──────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────

def home(request):
    upas = UPA.objects.filter(ativo=True)
    if upas.count() == 1:
        return redirect('entrar', upa_slug=upas.first().slug)
    return render(request, 'filas/home.html', {'upas': upas})


def login_view(request):
    if request.user.is_authenticated:
        return _redirecionar_pos_login(request.user)

    erro = None
    if request.method == 'POST':
        usuario = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if usuario:
            login(request, usuario)
            return _redirecionar_pos_login(usuario)
        erro = 'Usuário ou senha incorretos.'

    return render(request, 'filas/login.html', {'erro': erro})


def logout_view(request):
    logout(request)
    return redirect('login')


def _redirecionar_pos_login(usuario):
    if hasattr(usuario, 'perfil_diretor'):
        return redirect('dashboard')
    if hasattr(usuario, 'perfil'):
        return redirect('recepcao', upa_slug=usuario.perfil.upa.slug)
    return redirect('/admin/')


# ──────────────────────────────────────────
# DASHBOARD
# ──────────────────────────────────────────

@login_required
def dashboard(request):
    if not (request.user.is_superuser or hasattr(request.user, 'perfil_diretor')):
        return redirect('login')

    PERIODOS = [('hoje', 'Hoje'), ('semana', 'Esta semana'), ('mes', 'Este mês'), ('ano', 'Este ano')]
    periodo  = request.GET.get('periodo', 'hoje')
    if periodo not in dict(PERIODOS):
        periodo = 'hoje'

    agora = timezone.now()
    hoje  = agora.date()

    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
    elif periodo == 'ano':
        inicio = hoje.replace(month=1, day=1)
    else:
        inicio = hoje

    upa_diretor = request.user.perfil_diretor.upa if hasattr(request.user, 'perfil_diretor') else None
    upas = UPA.objects.filter(pk=upa_diretor.pk) if upa_diretor else UPA.objects.filter(ativo=True)

    base = Atendimento.objects.filter(criado_em__date__gte=inicio, criado_em__date__lte=hoje)
    if upa_diretor:
        base = base.filter(upa=upa_diretor)

    # ── Cards ──
    total_atendidos   = base.filter(status='atendido').count()
    total_ausentes    = base.filter(status='ausente').count()
    total_registrados = base.count()
    aguardando_agora  = Atendimento.objects.filter(status='aguardando').count()
    em_atendimento    = Atendimento.objects.filter(status='chamado').count()

    media_raw = base.filter(status='atendido', chamado_em__isnull=False).annotate(
        espera=ExpressionWrapper(F('chamado_em') - F('criado_em'), output_field=DurationField())
    ).aggregate(media=Avg('espera'))['media']
    tempo_medio = round(media_raw.total_seconds() / 60) if media_raw else 0

    # ── Donut: por tipo ──
    tipo_map   = dict(Atendimento.TIPOS)
    por_tipo   = {t: 0 for t in tipo_map}
    for row in base.filter(status='atendido').values('tipo').annotate(n=Count('id')):
        por_tipo[row['tipo']] = row['n']

    # ── Bar: por UPA ──
    por_upa = list(
        base.filter(status='atendido')
        .values('upa__nome').annotate(n=Count('id')).order_by('-n')
    )

    # ── Line: atendimentos por hora (hoje) ──
    por_hora = [0] * 24
    for row in (Atendimento.objects
                .filter(criado_em__date=hoje)
                .annotate(h=ExtractHour('criado_em'))
                .values('h').annotate(n=Count('id'))):
        por_hora[int(row['h'])] = row['n']

    # ── Tendência por dia ──
    tendencia_labels, tendencia_data = [], []
    if periodo != 'hoje':
        dia_map = {
            row['dia'].date(): row['n']
            for row in base.filter(status='atendido')
            .annotate(dia=TruncDay('criado_em')).values('dia').annotate(n=Count('id'))
        }
        for i in range((hoje - inicio).days + 1):
            d = inicio + timedelta(days=i)
            tendencia_labels.append(d.strftime('%d/%m'))
            tendencia_data.append(dia_map.get(d, 0))

    # ── Tabela ──
    tabela = []
    for upa in upas:
        upa_base = base.filter(upa=upa)
        row = {'upa': upa, 'tipos': {}, 'total': 0, 'ausentes': 0, 'tempo_medio': 0}
        for codigo, _ in Atendimento.TIPOS:
            n = upa_base.filter(tipo=codigo, status='atendido').count()
            row['tipos'][codigo] = n
            row['total'] += n
        row['ausentes'] = upa_base.filter(status='ausente').count()
        m = upa_base.filter(status='atendido', chamado_em__isnull=False).annotate(
            espera=ExpressionWrapper(F('chamado_em') - F('criado_em'), output_field=DurationField())
        ).aggregate(media=Avg('espera'))['media']
        row['tempo_medio'] = round(m.total_seconds() / 60) if m else 0
        tabela.append(row)

    import json
    return render(request, 'filas/dashboard.html', {
        'periodo': periodo,
        'periodos': PERIODOS,
        'inicio': inicio,
        'hoje': hoje,
        'total_atendidos':   total_atendidos,
        'total_ausentes':    total_ausentes,
        'total_registrados': total_registrados,
        'aguardando_agora':  aguardando_agora,
        'em_atendimento':    em_atendimento,
        'tempo_medio':       tempo_medio,
        'por_tipo_json':     json.dumps(por_tipo),
        'por_upa_json':      json.dumps(por_upa),
        'por_hora_json':     json.dumps(por_hora),
        'tendencia_labels':  json.dumps(tendencia_labels),
        'tendencia_data':    json.dumps(tendencia_data),
        'tabela':            tabela,
        'tipos':             Atendimento.TIPOS,
        'upa_diretor':       upa_diretor,
    })


# ──────────────────────────────────────────
# PACIENTE
# ──────────────────────────────────────────

def entrar(request, upa_slug):
    upa = get_object_or_404(UPA, slug=upa_slug, ativo=True)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        motivo     = request.POST.get('motivo_prioridade', '').strip()
        eh_prior   = request.POST.get('prioridade') == '1'
        if nome and tipo in dict(Atendimento.TIPOS):
            atendimento = Atendimento.objects.create(
                upa=upa, nome=nome, tipo=tipo,
                prioridade=eh_prior,
                motivo_prioridade=motivo if eh_prior else '',
            )
            return redirect('fila_paciente', upa_slug=upa_slug, pk=atendimento.pk)

    return render(request, 'filas/entrar.html', {
        'upa': upa,
        'tipos': Atendimento.TIPOS,
        'motivos_prioridade': Atendimento.MOTIVOS_PRIORIDADE,
    })


def fila_paciente(request, upa_slug, pk):
    upa = get_object_or_404(UPA, slug=upa_slug)
    atendimento = get_object_or_404(Atendimento, pk=pk, upa=upa)
    fila = Atendimento.objects.filter(
        upa=upa,
        tipo=atendimento.tipo,
        status='aguardando'
    ).order_by('criado_em')
    posicao = atendimento.posicao_na_fila()

    media = Atendimento.objects.filter(
        upa=upa,
        tipo=atendimento.tipo,
        status__in=['chamado', 'atendido'],
        criado_em__date=timezone.now().date(),
        chamado_em__isnull=False,
    ).annotate(
        espera=ExpressionWrapper(F('chamado_em') - F('criado_em'), output_field=DurationField())
    ).aggregate(media=Avg('espera'))['media']

    tempo_medio = round(media.total_seconds() / 60) if media else None

    return render(request, 'filas/fila_paciente.html', {
        'upa': upa,
        'atendimento': atendimento,
        'fila': fila,
        'posicao': posicao,
        'tempo_medio': tempo_medio,
    })


# ──────────────────────────────────────────
# RECEPÇÃO
# ──────────────────────────────────────────

@login_required
def recepcao(request, upa_slug):
    upa = get_object_or_404(UPA, slug=upa_slug, ativo=True)

    # Usuário comum só acessa a sua própria UPA
    if not request.user.is_staff:
        if not hasattr(request.user, 'perfil') or request.user.perfil.upa != upa:
            return redirect('recepcao', upa_slug=request.user.perfil.upa.slug)

    hoje = timezone.now().date()
    filas = {}
    for codigo, nome in Atendimento.TIPOS:
        filas[codigo] = {
            'nome': nome,
            'aguardando': Atendimento.objects.filter(
                upa=upa, tipo=codigo, status='aguardando', criado_em__date=hoje
            ).order_by('criado_em'),
            'chamados': Atendimento.objects.filter(
                upa=upa, tipo=codigo, status='chamado', criado_em__date=hoje
            ).order_by('-chamado_em'),
            'nao_compareceram': Atendimento.objects.filter(
                upa=upa, tipo=codigo, status='nao_compareceu', criado_em__date=hoje
            ).order_by('-chamado_em'),
        }

    return render(request, 'filas/recepcao.html', {
        'upa': upa,
        'filas': filas,
        'tipos': Atendimento.TIPOS,
    })


# ──────────────────────────────────────────
# AÇÕES
# ──────────────────────────────────────────

@login_required
@require_POST
def registrar_presencial(request, upa_slug):
    upa = get_object_or_404(UPA, slug=upa_slug)
    nome     = request.POST.get('nome', '').strip()
    tipo     = request.POST.get('tipo', '').strip()
    motivo   = request.POST.get('motivo_prioridade', '').strip()
    eh_prior = request.POST.get('prioridade') == '1'
    if nome and tipo in dict(Atendimento.TIPOS):
        atendimento = Atendimento.objects.create(
            upa=upa, nome=nome, tipo=tipo,
            origem='presencial',
            prioridade=eh_prior,
            motivo_prioridade=motivo if eh_prior else '',
        )
        return JsonResponse({'ok': True, 'senha': atendimento.senha, 'nome': atendimento.nome, 'tipo': atendimento.get_tipo_display()})
    return JsonResponse({'ok': False})


@login_required
@require_POST
def chamar_proximo(request, upa_slug, tipo):
    upa = get_object_or_404(UPA, slug=upa_slug)
    hoje = timezone.now().date()
    proximo = Atendimento.objects.filter(
        upa=upa, tipo=tipo, status='aguardando', criado_em__date=hoje
    ).order_by('criado_em').first()

    if proximo:
        proximo.chamar()
        _notificar(proximo, upa_slug)
        return JsonResponse({
            'ok': True,
            'senha': proximo.senha,
            'nome': proximo.nome,
            'pk': str(proximo.pk),
            'upa_slug': upa_slug,
            'presencial': proximo.origem == 'presencial',
        })

    return JsonResponse({'ok': False, 'mensagem': 'Fila vazia.'})


@login_required
@require_POST
def chamar_especifico(request, upa_slug, pk):
    upa = get_object_or_404(UPA, slug=upa_slug)
    atendimento = get_object_or_404(Atendimento, pk=pk, upa=upa)
    atendimento.chamar()
    _notificar(atendimento, upa_slug)
    return JsonResponse({'ok': True, 'senha': atendimento.senha, 'nome': atendimento.nome})


@login_required
@require_POST
def marcar_atendido(request, upa_slug, pk):
    upa = get_object_or_404(UPA, slug=upa_slug)
    get_object_or_404(Atendimento, pk=pk, upa=upa).atender()
    return redirect('recepcao', upa_slug=upa_slug)


@login_required
@require_POST
def marcar_ausente(request, upa_slug, pk):
    upa = get_object_or_404(UPA, slug=upa_slug)
    get_object_or_404(Atendimento, pk=pk, upa=upa).marcar_ausente()
    return redirect('recepcao', upa_slug=upa_slug)


@login_required
@require_POST
def marcar_nao_compareceu(request, upa_slug, pk):
    upa = get_object_or_404(UPA, slug=upa_slug)
    get_object_or_404(Atendimento, pk=pk, upa=upa).nao_compareceu()
    return JsonResponse({'ok': True})


@login_required
@require_POST
def reconvocar(request, upa_slug, pk):
    upa = get_object_or_404(UPA, slug=upa_slug)
    get_object_or_404(Atendimento, pk=pk, upa=upa).reconvocar()
    return redirect('recepcao', upa_slug=upa_slug)


# ──────────────────────────────────────────
# HELPER WebSocket
# ──────────────────────────────────────────

def _notificar(atendimento, upa_slug):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"fila_{upa_slug}_{atendimento.tipo}",
        {
            'type': 'senha_chamada',
            'senha': atendimento.senha,
            'nome': atendimento.nome,
            'atendimento_id': str(atendimento.pk),
        }
    )
