#!/usr/bin/env python3
"""
P2P Storage Demo

This script demonstrates the P2P storage system by:
1. Creating a simple network of nodes
2. Storing files
3. Retrieving files from different nodes
"""

import os
import time
import tempfile
from p2p_storage import P2PStorageNode


def main():
    print("=" * 60)
    print("P2P Storage System Demo")
    print("=" * 60)
    print()
    
    # Create temporary directory for demo
    temp_dir = tempfile.mkdtemp(prefix="p2p_demo_")
    print(f"Demo directory: {temp_dir}")
    print()
    
    # Create storage directories for each node
    storage_dir1 = os.path.join(temp_dir, "node1")
    storage_dir2 = os.path.join(temp_dir, "node2")
    storage_dir3 = os.path.join(temp_dir, "node3")
    
    # Step 1: Create and start three nodes
    print("Step 1: Creating P2P network with 3 nodes...")
    print("-" * 60)
    
    node1 = P2PStorageNode(host='localhost', port=6000, storage_dir=storage_dir1)
    node2 = P2PStorageNode(host='localhost', port=6001, storage_dir=storage_dir2)
    node3 = P2PStorageNode(host='localhost', port=6002, storage_dir=storage_dir3)
    
    node1.start()
    node2.start()
    node3.start()
    
    print(f"✓ Node 1 started: localhost:6000 (ID: {node1.node_id[:16]}...)")
    print(f"✓ Node 2 started: localhost:6001 (ID: {node2.node_id[:16]}...)")
    print(f"✓ Node 3 started: localhost:6002 (ID: {node3.node_id[:16]}...)")
    print()
    
    time.sleep(0.5)
    
    # Step 2: Connect nodes to form a network
    print("Step 2: Connecting nodes to form a network...")
    print("-" * 60)
    
    node2.connect_to_peer('localhost', 6000)
    node3.connect_to_peer('localhost', 6001)
    
    print("✓ Node 2 connected to Node 1")
    print("✓ Node 3 connected to Node 2")
    print()
    
    time.sleep(0.5)
    
    # Step 3: Show network status
    print("Step 3: Network Status")
    print("-" * 60)
    
    for i, node in enumerate([node1, node2, node3], 1):
        status = node.get_network_status()
        print(f"Node {i}:")
        print(f"  - Node ID: {status['node_id']}")
        print(f"  - Address: {status['host']}:{status['port']}")
        print(f"  - Connected Peers: {status['peers']}")
        print(f"  - Stored Files: {status['stored_files']}")
        print()
    
    # Step 4: Create test files
    print("Step 4: Creating test files...")
    print("-" * 60)
    
    test_file1 = os.path.join(temp_dir, "document.txt")
    test_file2 = os.path.join(temp_dir, "data.txt")
    
    with open(test_file1, 'w') as f:
        f.write("This is a test document for P2P storage.\n")
        f.write("It demonstrates file replication across nodes.\n")
    
    with open(test_file2, 'w') as f:
        f.write("Another file with different content.\n")
        f.write("P2P storage is decentralized and resilient.\n")
    
    print(f"✓ Created: {test_file1}")
    print(f"✓ Created: {test_file2}")
    print()
    
    # Step 5: Store files in the network
    print("Step 5: Storing files in the network...")
    print("-" * 60)
    
    hash1 = node1.store_file(test_file1)
    print(f"✓ Stored document.txt on Node 1")
    print(f"  File hash: {hash1}")
    
    time.sleep(0.5)
    
    hash2 = node3.store_file(test_file2)
    print(f"✓ Stored data.txt on Node 3")
    print(f"  File hash: {hash2}")
    print()
    
    time.sleep(0.5)
    
    # Step 6: Verify replication
    print("Step 6: Verifying file replication...")
    print("-" * 60)
    
    for i, node in enumerate([node1, node2, node3], 1):
        files = node.list_files()
        print(f"Node {i} has {len(files)} files:")
        for file_hash in files:
            print(f"  - {file_hash[:32]}...")
    print()
    
    # Step 7: Retrieve files from different nodes
    print("Step 7: Retrieving files from different nodes...")
    print("-" * 60)
    
    # Retrieve file stored on node1 from node3
    content = node3.retrieve_file(hash1)
    if content:
        print(f"✓ Retrieved document.txt from Node 3 (originally stored on Node 1)")
        print(f"  Content preview: {content[:50]}...")
    
    # Retrieve file stored on node3 from node1
    content = node1.retrieve_file(hash2)
    if content:
        print(f"✓ Retrieved data.txt from Node 1 (originally stored on Node 3)")
        print(f"  Content preview: {content[:50]}...")
    print()
    
    # Step 8: Test file retrieval after node failure
    print("Step 8: Testing resilience (simulating node failure)...")
    print("-" * 60)
    
    print("Stopping Node 1...")
    node1.stop()
    print("✓ Node 1 stopped")
    print()
    
    time.sleep(0.5)
    
    # Try to retrieve file from node2 (should still work due to replication)
    content = node2.retrieve_file(hash1)
    if content:
        print("✓ Still able to retrieve document.txt from Node 2!")
        print("  This demonstrates data redundancy in the P2P network.")
    else:
        print("✗ Could not retrieve file (replication may not have completed)")
    print()
    
    # Step 9: Cleanup
    print("Step 9: Cleaning up...")
    print("-" * 60)
    
    node2.stop()
    node3.stop()
    
    print("✓ All nodes stopped")
    print()
    
    # Summary
    print("=" * 60)
    print("Demo Summary")
    print("=" * 60)
    print("This demo showed:")
    print("  1. Creating a P2P network with multiple nodes")
    print("  2. Connecting nodes to form a decentralized network")
    print("  3. Storing files with automatic replication")
    print("  4. Retrieving files from any node in the network")
    print("  5. Network resilience - files remain accessible even if")
    print("     the original storage node goes offline")
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Decentralized architecture")
    print("  ✓ Automatic data replication")
    print("  ✓ Content-based addressing (using SHA-256 hashes)")
    print("  ✓ Network resilience and fault tolerance")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
