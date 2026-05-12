from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UPA, PerfilDiretor, PerfilRecepcionista, Atendimento


class DiretorInline(admin.StackedInline):
    model = PerfilDiretor
    can_delete = False
    verbose_name = 'Diretor'
    extra = 0


class PerfilInline(admin.StackedInline):
    model = PerfilRecepcionista
    can_delete = False
    verbose_name = 'Recepcionista'


class UserAdmin(BaseUserAdmin):
    inlines = [PerfilInline, DiretorInline]


@admin.register(PerfilDiretor)
class PerfilDiretorAdmin(admin.ModelAdmin):
    list_display = ('usuario',)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UPA)
class UPAAdmin(admin.ModelAdmin):
    list_display  = ('nome', 'slug', 'ativo', 'criado_em')
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(PerfilRecepcionista)
class PerfilRecepcionistaAdmin(admin.ModelAdmin):
    list_display  = ('usuario', 'upa')
    list_filter   = ('upa',)


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display  = ('senha', 'nome', 'upa', 'tipo', 'status', 'criado_em')
    list_filter   = ('upa', 'tipo', 'status')
    search_fields = ('nome', 'senha')
    ordering      = ('-criado_em',)
