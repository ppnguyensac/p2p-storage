#!/usr/bin/env python3
"""
P2P Storage CLI

Command-line interface for interacting with the P2P storage network.
"""

import argparse
import sys
import time
import os
from p2p_storage import P2PStorageNode


def main():
    parser = argparse.ArgumentParser(description='P2P Storage Network Node')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--storage-dir', help='Directory to store files (default: auto-generated)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a P2P storage node')
    start_parser.add_argument('--connect', help='Connect to an existing peer (format: host:port)')
    
    # Store command
    store_parser = subparsers.add_parser('store', help='Store a file in the network')
    store_parser.add_argument('file', help='Path to the file to store')
    store_parser.add_argument('--connect', help='Connect to node (format: host:port)', required=True)
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve a file from the network')
    retrieve_parser.add_argument('hash', help='Hash of the file to retrieve')
    retrieve_parser.add_argument('--output', '-o', help='Output file path', required=True)
    retrieve_parser.add_argument('--connect', help='Connect to node (format: host:port)', required=True)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List files on a node')
    list_parser.add_argument('--connect', help='Connect to node (format: host:port)', required=True)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get network status')
    status_parser.add_argument('--connect', help='Connect to node (format: host:port)', required=True)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'start':
        return start_node(args)
    elif args.command == 'store':
        return store_file(args)
    elif args.command == 'retrieve':
        return retrieve_file(args)
    elif args.command == 'list':
        return list_files(args)
    elif args.command == 'status':
        return get_status(args)
    
    return 0


def start_node(args):
    """Start a P2P storage node"""
    node = P2PStorageNode(host=args.host, port=args.port, storage_dir=args.storage_dir)
    node.start()
    
    print(f"Node started on {args.host}:{args.port}")
    print(f"Node ID: {node.node_id[:16]}...")
    print(f"Storage directory: {node.storage_dir}")
    
    # Connect to an existing peer if specified
    if args.connect:
        peer_host, peer_port = args.connect.split(':')
        peer_port = int(peer_port)
        print(f"\nConnecting to peer at {peer_host}:{peer_port}...")
        
        if node.connect_to_peer(peer_host, peer_port):
            print("Successfully connected to peer!")
        else:
            print("Failed to connect to peer")
    
    print("\nNode is running. Commands:")
    print("  status - Show network status")
    print("  list   - List stored files")
    print("  quit   - Stop the node")
    
    # Interactive mode
    try:
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'quit' or cmd == 'exit':
                break
            elif cmd == 'status':
                status = node.get_network_status()
                print(f"\nNode ID: {status['node_id']}")
                print(f"Address: {status['host']}:{status['port']}")
                print(f"Connected peers: {status['peers']}")
                print(f"Stored files: {status['stored_files']}")
                if status['peer_list']:
                    print("\nPeers:")
                    for peer in status['peer_list']:
                        print(f"  - {peer}")
            elif cmd == 'list':
                files = node.list_files()
                print(f"\nStored files ({len(files)}):")
                for file_hash in files:
                    print(f"  - {file_hash}")
            elif cmd == 'help':
                print("  status - Show network status")
                print("  list   - List stored files")
                print("  quit   - Stop the node")
            elif cmd:
                print("Unknown command. Type 'help' for available commands.")
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        node.stop()
    
    return 0


def store_file(args):
    """Store a file in the network"""
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        return 1
    
    # Parse peer address
    peer_host, peer_port = args.connect.split(':')
    peer_port = int(peer_port)
    
    # Create a temporary node to perform the operation
    node = P2PStorageNode(host='localhost', port=0)  # Port 0 for ephemeral port
    node.start()
    
    print(f"Connecting to peer at {peer_host}:{peer_port}...")
    if not node.connect_to_peer(peer_host, peer_port):
        print("Failed to connect to peer")
        node.stop()
        return 1
    
    print(f"Storing file: {args.file}")
    try:
        file_hash = node.store_file(args.file)
        print(f"File stored successfully!")
        print(f"File hash: {file_hash}")
        print(f"\nTo retrieve this file, use:")
        print(f"  python3 p2p_cli.py retrieve {file_hash} -o <output_file> --connect {peer_host}:{peer_port}")
    except Exception as e:
        print(f"Error storing file: {e}")
        node.stop()
        return 1
    
    node.stop()
    return 0


def retrieve_file(args):
    """Retrieve a file from the network"""
    # Parse peer address
    peer_host, peer_port = args.connect.split(':')
    peer_port = int(peer_port)
    
    # Create a temporary node to perform the operation
    node = P2PStorageNode(host='localhost', port=0)  # Port 0 for ephemeral port
    node.start()
    
    print(f"Connecting to peer at {peer_host}:{peer_port}...")
    if not node.connect_to_peer(peer_host, peer_port):
        print("Failed to connect to peer")
        node.stop()
        return 1
    
    print(f"Retrieving file: {args.hash}")
    try:
        content = node.retrieve_file(args.hash)
        if content:
            with open(args.output, 'w') as f:
                f.write(content)
            print(f"File retrieved successfully!")
            print(f"Saved to: {args.output}")
        else:
            print("File not found in the network")
            node.stop()
            return 1
    except Exception as e:
        print(f"Error retrieving file: {e}")
        node.stop()
        return 1
    
    node.stop()
    return 0


def list_files(args):
    """List files on a node"""
    # Parse peer address
    peer_host, peer_port = args.connect.split(':')
    peer_port = int(peer_port)
    
    # Create a temporary node to perform the operation
    node = P2PStorageNode(host='localhost', port=0)
    node.start()
    
    print(f"Connecting to peer at {peer_host}:{peer_port}...")
    try:
        request = {'action': 'LIST'}
        response = node._send_request(peer_host, peer_port, request)
        
        if response.get('status') == 'success':
            files = response.get('files', [])
            print(f"\nStored files ({len(files)}):")
            for file_hash in files:
                print(f"  - {file_hash}")
        else:
            print(f"Error: {response.get('message')}")
            node.stop()
            return 1
    except Exception as e:
        print(f"Error listing files: {e}")
        node.stop()
        return 1
    
    node.stop()
    return 0


def get_status(args):
    """Get network status"""
    # Parse peer address
    peer_host, peer_port = args.connect.split(':')
    peer_port = int(peer_port)
    
    # Create a temporary node to perform the operation
    node = P2PStorageNode(host='localhost', port=0)
    node.start()
    
    print(f"Connecting to peer at {peer_host}:{peer_port}...")
    try:
        request = {'action': 'PING'}
        response = node._send_request(peer_host, peer_port, request)
        
        if response.get('status') == 'success':
            print(f"\nNode ID: {response.get('node_id', 'Unknown')[:16]}...")
            print(f"Status: Online")
            print(f"Address: {peer_host}:{peer_port}")
        else:
            print(f"Error: {response.get('message')}")
            node.stop()
            return 1
    except Exception as e:
        print(f"Error getting status: {e}")
        node.stop()
        return 1
    
    node.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
