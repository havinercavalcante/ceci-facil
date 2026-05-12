import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cecifacil.settings')

django_asgi_app = get_asgi_application()

from filas.consumers import FilaConsumer

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter([
            re_path(r'ws/fila/(?P<upa_slug>[\w-]+)/(?P<tipo>\w+)/$', FilaConsumer.as_asgi()),
        ])
    ),
})
