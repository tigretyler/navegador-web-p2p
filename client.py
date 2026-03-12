import socket
import json
import asyncio
import aiohttp
from datetime import datetime

class P2PClient:
    def __init__(self, node_id, server_host='localhost', server_port=8080):
        self.node_id = node_id
        self.server_host = server_host
        self.server_port = server_port
        self.ws = None
        self.tcp_socket = None
        self.udp_socket = None
        self.peers = {}
        
    async def connect_websocket(self):
        """Connect to P2P server via WebSocket"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f'ws://{self.server_host}:{self.server_port}/ws') as ws:
                    self.ws = ws
                    print(f'Connected to server at ws://{self.server_host}:{self.server_port}/ws')
                    
                    # Register node
                    await self.register_node()
                    
                    # Listen for messages
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self.handle_message(json.loads(msg.data))
        except Exception as e:
            print(f'WebSocket connection error: {e}')
    
    async def register_node(self):
        """Register this node with the server"""
        message = {
            'type': 'register',
            'node_id': self.node_id,
            'host': 'localhost',
            'ws_port': 8080,
            'tcp_port': 9000,
            'udp_port': 9001,
            'timestamp': datetime.now().isoformat()
        }
        await self.ws.send_str(json.dumps(message))
        print(f'Node {self.node_id} registered')
    
    async def discover_nodes(self):
        """Discover available nodes in the network"""
        message = {'type': 'discover'}
        await self.ws.send_str(json.dumps(message))
    
    async def send_message(self, target_node_id, content):
        """Send message to another peer"""
        message = {
            'type': 'message',
            'from': self.node_id,
            'target': target_node_id,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        await self.ws.send_str(json.dumps(message))
        print(f'Message sent to {target_node_id}: {content}')
    
    async def handle_message(self, data):
        """Handle incoming messages"""
        msg_type = data.get('type')
        
        if msg_type == 'nodes':
            self.peers = data.get('data', {})
            print(f'Available peers: {list(self.peers.keys())}')
        
        elif msg_type == 'node_registered':
            node_id = data.get('node_id')
            print(f'Node registered: {node_id}')
            self.peers = data.get('nodes', {})
        
        elif msg_type == 'message':
            sender = data.get('from')
            content = data.get('content')
            print(f'Message from {sender}: {content}')
    
    def connect_tcp(self, target_host, target_port):
        """Connect to peer via TCP"""
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((target_host, target_port))
            print(f'TCP connection established with {target_host}:{target_port}')
        except Exception as e:
            print(f'TCP connection error: {e}')
    
    def send_tcp(self, data):
        """Send data via TCP"""
        if self.tcp_socket:
            self.tcp_socket.send(data.encode())
    
    def send_udp(self, target_host, target_port, data):
        """Send data via UDP"""
        try:
            if not self.udp_socket:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.sendto(data.encode(), (target_host, target_port))
            print(f'UDP message sent to {target_host}:{target_port}')
        except Exception as e:
            print(f'UDP error: {e}')
    
    async def run(self):
        """Run the client"""
        await self.connect_websocket()

async def main():
    client = P2PClient('peer-1')
    await client.run()

if __name__ == '__main__':
    asyncio.run(main())