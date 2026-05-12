import json
from channels.generic.websocket import AsyncWebsocketConsumer


class FilaConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.upa_slug   = self.scope['url_route']['kwargs']['upa_slug']
        self.tipo       = self.scope['url_route']['kwargs']['tipo']
        self.group_name = f"fila_{self.upa_slug}_{self.tipo}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def senha_chamada(self, event):
        await self.send(text_data=json.dumps({
            'tipo': 'senha_chamada',
            'senha': event['senha'],
            'nome': event['nome'],
            'atendimento_id': event['atendimento_id'],
        }))
