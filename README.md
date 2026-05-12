# CeciFácil — Sistema de Filas para UPA

Sistema de gerenciamento de filas para Unidades de Pronto Atendimento (UPA), com suporte a múltiplas unidades, atendimento online e presencial, painel de recepção em tempo real e dashboard gerencial.

---

## Funcionalidades

- Múltiplas UPAs no mesmo sistema, cada uma com filas independentes
- Entrada na fila pelo celular (online) ou pela recepção (presencial)
- Tipos de atendimento: Consulta, Vacina, Curativo, Farmácia
- Marcação de prioridade com motivo (idoso, gestante, deficiência, criança)
- Painel da recepção com atualização automática e WebSocket
- Fluxo de chamada: Agora → Não compareceu → Reconvocar / Remover
- Dashboard gerencial por período (dia, semana, mês, ano)
- Três perfis de acesso: Paciente, Recepcionista, Diretor

---

## Como rodar

### 1. Ambiente virtual
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2. Dependências
```bash
pip install -r requirements.txt
```

### 3. Banco de dados (PostgreSQL)

> Se outra aplicação estiver usando a porta 5432, configure o PostgreSQL para usar a porta 5433 em `/etc/postgresql/16/main/postgresql.conf` e ajuste o `.env`.

```sql
CREATE USER cecifacil_user WITH PASSWORD 'suasenha123';
CREATE DATABASE cecifacil OWNER cecifacil_user;
GRANT ALL PRIVILEGES ON DATABASE cecifacil TO cecifacil_user;
```

### 4. Variáveis de ambiente
```bash
cp .env.example .env
# Edite .env com SECRET_KEY, senha do banco e porta
```

### 5. Migrações
```bash
python manage.py migrate
```

### 6. Dados iniciais (UPAs e usuários)
```bash
python manage.py shell
```
```python
from django.contrib.auth.models import User
from filas.models import UPA, PerfilRecepcionista, PerfilDiretor

upa = UPA.objects.create(nome="UPA Central", slug="upa-central")

# Superusuário (admin Django)
User.objects.create_superuser('admin', '', 'admin123')

# Recepcionista
u = User.objects.create_user('recepcao', '', 'rec123')
PerfilRecepcionista.objects.create(usuario=u, upa=upa)

# Diretor
d = User.objects.create_user('diretor', '', 'dir123')
PerfilDiretor.objects.create(usuario=d, upa=upa)
```

### 7. Servidor
```bash
python manage.py runserver
```

---

## URLs

| Tela | URL |
|---|---|
| Home (seleção de UPA) | `http://localhost:8000/` |
| Paciente entra na fila | `http://localhost:8000/<upa-slug>/` |
| Acompanhar fila (celular) | `http://localhost:8000/<upa-slug>/fila/<uuid>/` |
| Login da equipe | `http://localhost:8000/login/` |
| Painel da recepção | `http://localhost:8000/<upa-slug>/recepcao/` |
| Dashboard do diretor | `http://localhost:8000/dashboard/` |
| Admin Django | `http://localhost:8000/admin/` |

---

## Perfis de acesso

| Perfil | Acesso | Como criar |
|---|---|---|
| Paciente | Sem login — acessa pela URL da UPA | — |
| Recepcionista | Painel da recepção da sua UPA | `PerfilRecepcionista` no admin |
| Diretor | Dashboard da sua UPA | `PerfilDiretor` no admin |
| Admin | Tudo (`/admin/`) | `createsuperuser` |

---

## Estrutura

```
cecifacil/
├── cecifacil/
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py             # WebSocket (Django Channels)
├── filas/
│   ├── models.py           # UPA, Atendimento, PerfilRecepcionista, PerfilDiretor
│   ├── views.py
│   ├── consumers.py        # WebSocket consumer por UPA/tipo
│   ├── tasks.py            # Reset diário das filas
│   ├── urls.py
│   ├── admin.py
│   └── templatetags/
│       └── filas_extras.py
├── templates/filas/
│   ├── base.html
│   ├── home.html           # Seleção de UPA
│   ├── entrar.html         # Paciente entra na fila
│   ├── fila_paciente.html  # Acompanhamento pelo celular
│   ├── recepcao.html       # Painel da recepção
│   ├── dashboard.html      # Dashboard do diretor
│   └── login.html
├── .env.example
├── requirements.txt
└── manage.py
```

---

## Reset automático das filas

As filas são zeradas automaticamente à meia-noite via cron:
```bash
python manage.py crontab add
```
