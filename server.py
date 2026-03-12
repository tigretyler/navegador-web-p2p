import asyncio
import json
import socket
import threading
from aiohttp import web
import aiohttp
from datetime import datetime

class P2PServer:
    def __init__(self, host='0.0.0.0', ws_port=8080, tcp_port=9000, udp_port=9001):
        self.host = host
        self.ws_port = ws_port
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.nodes = {}  # {node_id: {host, ws_port, tcp_port, udp_port, timestamp}}
        self.websocket_connections = set()
        
    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websocket_connections.add(ws)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.process_message(data, ws)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
        finally:
            self.websocket_connections.discard(ws)
        
        return ws
    
    async def process_message(self, data, ws):
        msg_type = data.get('type')
        
        if msg_type == 'register':
            node_id = data.get('node_id')
            self.nodes[node_id] = {
                'host': data.get('host'),
                'ws_port': data.get('ws_port'),
                'tcp_port': data.get('tcp_port'),
                'udp_port': data.get('udp_port'),
                'timestamp': datetime.now().isoformat()
            }
            await self.broadcast({'type': 'node_registered', 'node_id': node_id, 'nodes': self.nodes})
        
        elif msg_type == 'discover':
            await ws.send_str(json.dumps({'type': 'nodes', 'data': self.nodes}))
        
        elif msg_type == 'message':
            target_id = data.get('target')
            if target_id in self.nodes:
                await self.broadcast(data)
    
    async def broadcast(self, message):
        for ws in self.websocket_connections:
            try:
                await ws.send_str(json.dumps(message))
            except:
                pass
    
    async def start_web_server(self):
        app = web.Application()
        app.router.add_get('/ws', self.handle_websocket)
        app.router.add_static('/', path='web', name='static')
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.ws_port)
        await site.start()
        print(f'WebSocket server started on ws://{self.host}:{self.ws_port}')
    
    def start_tcp_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.tcp_port))
        server_socket.listen(5)
        print(f'TCP server listening on {self.host}:{self.tcp_port}')
        
        while True:
            client_socket, address = server_socket.accept()
            print(f'TCP connection from {address}')
            client_socket.close()
    
    def start_udp_server(self):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.bind((self.host, self.udp_port))
        print(f'UDP server listening on {self.host}:{self.udp_port}')
        
        while True:
            data, address = udp_socket.recvfrom(1024)
            print(f'UDP message from {address}: {data.decode()}')
    
    def run(self):
        # Start TCP server in thread
        tcp_thread = threading.Thread(target=self.start_tcp_server, daemon=True)
        tcp_thread.start()
        
        # Start UDP server in thread
        udp_thread = threading.Thread(target=self.start_udp_server, daemon=True)
        udp_thread.start()
        
        # Start WebSocket server
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start_web_server())
        loop.run_forever()

if __name__ == '__main__':
    server = P2PServer()
    server.run()