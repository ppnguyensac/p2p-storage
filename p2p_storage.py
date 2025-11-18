"""
P2P Storage Node Implementation

This module implements a peer-to-peer storage node that can:
- Store and retrieve files in a distributed manner
- Communicate with other peers in the network
- Use a DHT (Distributed Hash Table) for file discovery
- Replicate data for redundancy
"""

import socket
import threading
import json
import hashlib
import os
import time
from typing import Dict, List, Tuple, Optional, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class DHTNode:
    """Distributed Hash Table Node for file discovery"""
    
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.routing_table: Dict[str, Tuple[str, int]] = {}  # node_id -> (host, port)
        self.stored_keys: Dict[str, str] = {}  # file_hash -> file_path
        self.logger = logging.getLogger(f"DHTNode-{node_id}")
    
    def add_peer(self, peer_id: str, host: str, port: int):
        """Add a peer to the routing table"""
        self.routing_table[peer_id] = (host, port)
        self.logger.info(f"Added peer {peer_id} at {host}:{port}")
    
    def remove_peer(self, peer_id: str):
        """Remove a peer from the routing table"""
        if peer_id in self.routing_table:
            del self.routing_table[peer_id]
            self.logger.info(f"Removed peer {peer_id}")
    
    def find_node(self, key: str) -> Optional[Tuple[str, int]]:
        """Find the node responsible for a given key"""
        # Simple implementation: find closest node ID to key
        if not self.routing_table:
            return None
        
        closest_id = min(self.routing_table.keys(), 
                        key=lambda x: self._distance(x, key))
        return self.routing_table[closest_id]
    
    def store_key(self, file_hash: str, file_path: str):
        """Store a key-value pair in the DHT"""
        self.stored_keys[file_hash] = file_path
        self.logger.info(f"Stored key {file_hash} -> {file_path}")
    
    def lookup_key(self, file_hash: str) -> Optional[str]:
        """Lookup a key in the DHT"""
        return self.stored_keys.get(file_hash)
    
    @staticmethod
    def _distance(id1: str, id2: str) -> int:
        """Calculate XOR distance between two IDs"""
        # Convert to hex if not already
        try:
            hash1 = int(id1, 16)
        except ValueError:
            hash1 = int(hashlib.sha256(id1.encode()).hexdigest(), 16)
        
        try:
            hash2 = int(id2, 16)
        except ValueError:
            hash2 = int(hashlib.sha256(id2.encode()).hexdigest(), 16)
        
        return hash1 ^ hash2


class P2PStorageNode:
    """Main P2P Storage Node"""
    
    def __init__(self, host: str = 'localhost', port: int = 5000, storage_dir: str = None):
        self.host = host
        self.port = port
        self.node_id = self._generate_node_id()
        
        # Storage directory
        if storage_dir is None:
            storage_dir = f"node_data_{self.node_id[:8]}"
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # DHT
        self.dht = DHTNode(self.node_id, host, port)
        
        # Network
        self.socket = None
        self.running = False
        self.server_thread = None
        
        self.logger = logging.getLogger(f"P2PNode-{self.node_id[:8]}")
    
    def _generate_node_id(self) -> str:
        """Generate a unique node ID based on host:port and timestamp"""
        data = f"{self.host}:{self.port}:{time.time()}".encode()
        return hashlib.sha256(data).hexdigest()
    
    def start(self):
        """Start the P2P node"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        
        self.server_thread = threading.Thread(target=self._listen_for_connections, daemon=True)
        self.server_thread.start()
        
        self.logger.info(f"Node started on {self.host}:{self.port} with ID {self.node_id[:8]}")
    
    def stop(self):
        """Stop the P2P node"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.logger.info("Node stopped")
    
    def _listen_for_connections(self):
        """Listen for incoming connections from peers"""
        while self.running:
            try:
                self.socket.settimeout(1.0)
                client_socket, address = self.socket.accept()
                threading.Thread(target=self._handle_client, args=(client_socket, address), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.logger.error(f"Error accepting connection: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle incoming client requests"""
        try:
            data = client_socket.recv(4096).decode()
            if not data:
                return
            
            request = json.loads(data)
            response = self._process_request(request)
            
            client_socket.send(json.dumps(response).encode())
        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests"""
        action = request.get('action')
        
        if action == 'PING':
            return {'status': 'success', 'message': 'PONG', 'node_id': self.node_id}
        
        elif action == 'STORE':
            file_hash = request.get('file_hash')
            content = request.get('content')
            if file_hash and content:
                file_path = self._store_file(file_hash, content)
                return {'status': 'success', 'message': 'File stored', 'path': file_path}
            return {'status': 'error', 'message': 'Missing file_hash or content'}
        
        elif action == 'RETRIEVE':
            file_hash = request.get('file_hash')
            if file_hash:
                content = self._retrieve_file(file_hash)
                if content:
                    return {'status': 'success', 'content': content}
                return {'status': 'error', 'message': 'File not found'}
            return {'status': 'error', 'message': 'Missing file_hash'}
        
        elif action == 'JOIN':
            peer_id = request.get('peer_id')
            peer_host = request.get('peer_host')
            peer_port = request.get('peer_port')
            if peer_id and peer_host and peer_port:
                self.dht.add_peer(peer_id, peer_host, peer_port)
                return {'status': 'success', 'message': 'Peer added', 'node_id': self.node_id}
            return {'status': 'error', 'message': 'Missing peer information'}
        
        elif action == 'LIST':
            files = self.list_files()
            return {'status': 'success', 'files': files}
        
        return {'status': 'error', 'message': 'Unknown action'}
    
    def _store_file(self, file_hash: str, content: str) -> str:
        """Store file content locally"""
        file_path = os.path.join(self.storage_dir, file_hash)
        with open(file_path, 'w') as f:
            f.write(content)
        self.dht.store_key(file_hash, file_path)
        self.logger.info(f"Stored file {file_hash}")
        return file_path
    
    def _retrieve_file(self, file_hash: str) -> Optional[str]:
        """Retrieve file content locally"""
        file_path = os.path.join(self.storage_dir, file_hash)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read()
        return None
    
    def connect_to_peer(self, peer_host: str, peer_port: int) -> bool:
        """Connect to another peer in the network"""
        try:
            request = {
                'action': 'JOIN',
                'peer_id': self.node_id,
                'peer_host': self.host,
                'peer_port': self.port
            }
            response = self._send_request(peer_host, peer_port, request)
            
            if response.get('status') == 'success':
                peer_id = response.get('node_id')
                self.dht.add_peer(peer_id, peer_host, peer_port)
                self.logger.info(f"Connected to peer at {peer_host}:{peer_port}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error connecting to peer {peer_host}:{peer_port}: {e}")
            return False
    
    def _send_request(self, host: str, port: int, request: Dict[str, Any], timeout: int = 5) -> Dict[str, Any]:
        """Send a request to another node"""
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(timeout)
        
        try:
            client_socket.connect((host, port))
            client_socket.send(json.dumps(request).encode())
            response_data = client_socket.recv(4096).decode()
            return json.loads(response_data)
        finally:
            client_socket.close()
    
    def store_file(self, file_path: str) -> str:
        """Store a file in the P2P network"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Calculate file hash
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Store locally
        self._store_file(file_hash, content)
        
        # Replicate to peers
        for peer_id, (peer_host, peer_port) in self.dht.routing_table.items():
            try:
                request = {
                    'action': 'STORE',
                    'file_hash': file_hash,
                    'content': content
                }
                self._send_request(peer_host, peer_port, request)
                self.logger.info(f"Replicated file {file_hash} to peer {peer_id[:8]}")
            except Exception as e:
                self.logger.error(f"Failed to replicate to peer {peer_id[:8]}: {e}")
        
        return file_hash
    
    def retrieve_file(self, file_hash: str) -> Optional[str]:
        """Retrieve a file from the P2P network"""
        # Try local first
        content = self._retrieve_file(file_hash)
        if content:
            return content
        
        # Try peers
        for peer_id, (peer_host, peer_port) in self.dht.routing_table.items():
            try:
                request = {'action': 'RETRIEVE', 'file_hash': file_hash}
                response = self._send_request(peer_host, peer_port, request)
                
                if response.get('status') == 'success':
                    content = response.get('content')
                    # Store locally for caching
                    self._store_file(file_hash, content)
                    return content
            except Exception as e:
                self.logger.error(f"Failed to retrieve from peer {peer_id[:8]}: {e}")
        
        return None
    
    def list_files(self) -> List[str]:
        """List all files stored on this node"""
        if not os.path.exists(self.storage_dir):
            return []
        return [f for f in os.listdir(self.storage_dir) if os.path.isfile(os.path.join(self.storage_dir, f))]
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get the status of the P2P network"""
        return {
            'node_id': self.node_id[:8],
            'host': self.host,
            'port': self.port,
            'peers': len(self.dht.routing_table),
            'stored_files': len(self.list_files()),
            'peer_list': [f"{peer_id[:8]}@{host}:{port}" for peer_id, (host, port) in self.dht.routing_table.items()]
        }
