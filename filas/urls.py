from django.urls import path
from . import views

urlpatterns = [
    path('',         views.home, name='home'),
    path('login/',     views.login_view,  name='login'),
    path('logout/',    views.logout_view, name='logout'),
    path('dashboard/', views.dashboard,   name='dashboard'),

    path('<slug:upa_slug>/',                              views.entrar,           name='entrar'),
    path('<slug:upa_slug>/fila/<uuid:pk>/',               views.fila_paciente,    name='fila_paciente'),
    path('<slug:upa_slug>/recepcao/',                     views.recepcao,         name='recepcao'),
    path('<slug:upa_slug>/registrar/',                    views.registrar_presencial, name='registrar_presencial'),
    path('<slug:upa_slug>/chamar/proximo/<str:tipo>/',    views.chamar_proximo,   name='chamar_proximo'),
    path('<slug:upa_slug>/chamar/<uuid:pk>/',             views.chamar_especifico,name='chamar_especifico'),
    path('<slug:upa_slug>/atendido/<uuid:pk>/',           views.marcar_atendido,  name='marcar_atendido'),
    path('<slug:upa_slug>/ausente/<uuid:pk>/',            views.marcar_ausente,   name='marcar_ausente'),
    path('<slug:upa_slug>/nao-compareceu/<uuid:pk>/',      views.marcar_nao_compareceu, name='nao_compareceu'),
    path('<slug:upa_slug>/reconvocar/<uuid:pk>/',         views.reconvocar,       name='reconvocar'),
]
