"""
Unit tests for P2P Storage System
"""

import unittest
import os
import time
import tempfile
import shutil
from p2p_storage import P2PStorageNode, DHTNode


class TestDHTNode(unittest.TestCase):
    """Test cases for DHT functionality"""
    
    def setUp(self):
        self.dht = DHTNode("test_node_id", "localhost", 5000)
    
    def test_add_peer(self):
        """Test adding a peer to the routing table"""
        self.dht.add_peer("peer1", "localhost", 5001)
        self.assertIn("peer1", self.dht.routing_table)
        self.assertEqual(self.dht.routing_table["peer1"], ("localhost", 5001))
    
    def test_remove_peer(self):
        """Test removing a peer from the routing table"""
        self.dht.add_peer("peer1", "localhost", 5001)
        self.dht.remove_peer("peer1")
        self.assertNotIn("peer1", self.dht.routing_table)
    
    def test_store_and_lookup_key(self):
        """Test storing and looking up keys"""
        file_hash = "abc123"
        file_path = "/tmp/test.txt"
        
        self.dht.store_key(file_hash, file_path)
        result = self.dht.lookup_key(file_hash)
        
        self.assertEqual(result, file_path)
    
    def test_lookup_nonexistent_key(self):
        """Test looking up a key that doesn't exist"""
        result = self.dht.lookup_key("nonexistent")
        self.assertIsNone(result)
    
    def test_find_node(self):
        """Test finding the closest node for a key"""
        self.dht.add_peer("peer1", "localhost", 5001)
        self.dht.add_peer("peer2", "localhost", 5002)
        
        result = self.dht.find_node("somekey")
        self.assertIsNotNone(result)
        self.assertIn(result, [("localhost", 5001), ("localhost", 5002)])
    
    def test_find_node_empty_table(self):
        """Test finding a node when routing table is empty"""
        result = self.dht.find_node("somekey")
        self.assertIsNone(result)


class TestP2PStorageNode(unittest.TestCase):
    """Test cases for P2P Storage Node"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir1 = os.path.join(self.temp_dir, "node1")
        self.storage_dir2 = os.path.join(self.temp_dir, "node2")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_node_creation(self):
        """Test creating a P2P node"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        self.assertEqual(node.host, 'localhost')
        self.assertEqual(node.port, 5100)
        self.assertIsNotNone(node.node_id)
        self.assertTrue(os.path.exists(self.storage_dir1))
    
    def test_node_id_generation(self):
        """Test that node IDs are unique"""
        node1 = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        time.sleep(0.01)  # Small delay to ensure different timestamp
        node2 = P2PStorageNode(host='localhost', port=5101, storage_dir=self.storage_dir2)
        
        self.assertNotEqual(node1.node_id, node2.node_id)
    
    def test_start_stop_node(self):
        """Test starting and stopping a node"""
        node = P2PStorageNode(host='localhost', port=5104, storage_dir=self.storage_dir1)
        
        node.start()
        self.assertTrue(node.running)
        self.assertIsNotNone(node.socket)
        
        node.stop()
        self.assertFalse(node.running)
    
    def test_store_file_locally(self):
        """Test storing a file locally"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        file_hash = "test_hash_123"
        content = "Hello, P2P Storage!"
        
        file_path = node._store_file(file_hash, content)
        
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'r') as f:
            stored_content = f.read()
        self.assertEqual(stored_content, content)
    
    def test_retrieve_file_locally(self):
        """Test retrieving a file locally"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        file_hash = "test_hash_456"
        content = "Test content for retrieval"
        
        node._store_file(file_hash, content)
        retrieved_content = node._retrieve_file(file_hash)
        
        self.assertEqual(retrieved_content, content)
    
    def test_retrieve_nonexistent_file(self):
        """Test retrieving a file that doesn't exist"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        content = node._retrieve_file("nonexistent_hash")
        self.assertIsNone(content)
    
    def test_list_files(self):
        """Test listing files on a node"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        # Store multiple files
        node._store_file("hash1", "content1")
        node._store_file("hash2", "content2")
        node._store_file("hash3", "content3")
        
        files = node.list_files()
        
        self.assertEqual(len(files), 3)
        self.assertIn("hash1", files)
        self.assertIn("hash2", files)
        self.assertIn("hash3", files)
    
    def test_network_status(self):
        """Test getting network status"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        node.start()
        
        # Add some peers
        node.dht.add_peer("peer1", "localhost", 5001)
        node.dht.add_peer("peer2", "localhost", 5002)
        
        # Store some files
        node._store_file("hash1", "content1")
        
        status = node.get_network_status()
        
        self.assertIn('node_id', status)
        self.assertEqual(status['host'], 'localhost')
        self.assertEqual(status['port'], 5100)
        self.assertEqual(status['peers'], 2)
        self.assertEqual(status['stored_files'], 1)
        
        node.stop()
    
    def test_peer_connection(self):
        """Test connecting two peers"""
        node1 = P2PStorageNode(host='localhost', port=5105, storage_dir=self.storage_dir1)
        node2 = P2PStorageNode(host='localhost', port=5106, storage_dir=self.storage_dir2)
        
        node1.start()
        node2.start()
        
        time.sleep(0.5)  # Give nodes time to start
        
        # Connect node2 to node1
        success = node2.connect_to_peer('localhost', 5105)
        
        self.assertTrue(success)
        self.assertEqual(len(node2.dht.routing_table), 1)
        
        node1.stop()
        node2.stop()
    
    def test_file_replication(self):
        """Test file replication across peers"""
        node1 = P2PStorageNode(host='localhost', port=5102, storage_dir=self.storage_dir1)
        node2 = P2PStorageNode(host='localhost', port=5103, storage_dir=self.storage_dir2)
        
        node1.start()
        node2.start()
        
        time.sleep(0.5)
        
        # Connect the nodes
        node2.connect_to_peer('localhost', 5102)
        
        time.sleep(0.5)
        
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content for replication")
        
        # Store file on node2 (should replicate to node1)
        file_hash = node2.store_file(test_file)
        
        time.sleep(0.5)
        
        # Verify file exists on both nodes
        content1 = node1._retrieve_file(file_hash)
        content2 = node2._retrieve_file(file_hash)
        
        self.assertIsNotNone(content2)
        self.assertEqual(content1, content2)
        
        node1.stop()
        node2.stop()
    
    def test_process_ping_request(self):
        """Test processing PING request"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        request = {'action': 'PING'}
        response = node._process_request(request)
        
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['message'], 'PONG')
        self.assertIn('node_id', response)
    
    def test_process_store_request(self):
        """Test processing STORE request"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        request = {
            'action': 'STORE',
            'file_hash': 'test_hash',
            'content': 'test content'
        }
        response = node._process_request(request)
        
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['message'], 'File stored')
        
        # Verify file was actually stored
        content = node._retrieve_file('test_hash')
        self.assertEqual(content, 'test content')
    
    def test_process_retrieve_request(self):
        """Test processing RETRIEVE request"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        # Store a file first
        node._store_file('test_hash', 'test content')
        
        request = {
            'action': 'RETRIEVE',
            'file_hash': 'test_hash'
        }
        response = node._process_request(request)
        
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['content'], 'test content')
    
    def test_process_list_request(self):
        """Test processing LIST request"""
        node = P2PStorageNode(host='localhost', port=5100, storage_dir=self.storage_dir1)
        
        # Store some files
        node._store_file('hash1', 'content1')
        node._store_file('hash2', 'content2')
        
        request = {'action': 'LIST'}
        response = node._process_request(request)
        
        self.assertEqual(response['status'], 'success')
        self.assertIn('files', response)
        self.assertEqual(len(response['files']), 2)


class TestP2PIntegration(unittest.TestCase):
    """Integration tests for P2P network"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.nodes = []
    
    def tearDown(self):
        """Clean up test fixtures"""
        for node in self.nodes:
            try:
                node.stop()
            except:
                pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_three_node_network(self):
        """Test a network with three nodes"""
        # Create three nodes
        storage_dirs = [os.path.join(self.temp_dir, f"node{i}") for i in range(3)]
        
        node1 = P2PStorageNode(host='localhost', port=5200, storage_dir=storage_dirs[0])
        node2 = P2PStorageNode(host='localhost', port=5201, storage_dir=storage_dirs[1])
        node3 = P2PStorageNode(host='localhost', port=5202, storage_dir=storage_dirs[2])
        
        self.nodes = [node1, node2, node3]
        
        # Start all nodes
        for node in self.nodes:
            node.start()
        
        time.sleep(0.5)
        
        # Connect them in a chain: node2 -> node1, node3 -> node2
        node2.connect_to_peer('localhost', 5200)
        node3.connect_to_peer('localhost', 5201)
        
        time.sleep(0.5)
        
        # Verify connections
        # node1 should have 1 peer (node2)
        self.assertEqual(len(node1.dht.routing_table), 1)
        # node2 should have 2 peers (node1 and node3)
        self.assertEqual(len(node2.dht.routing_table), 2)
        # node3 should have 1 peer (node2)
        self.assertEqual(len(node3.dht.routing_table), 1)
    
    def test_file_distribution(self):
        """Test file distribution across network"""
        # Create two nodes
        storage_dirs = [os.path.join(self.temp_dir, f"node{i}") for i in range(2)]
        
        node1 = P2PStorageNode(host='localhost', port=5210, storage_dir=storage_dirs[0])
        node2 = P2PStorageNode(host='localhost', port=5211, storage_dir=storage_dirs[1])
        
        self.nodes = [node1, node2]
        
        # Start nodes
        node1.start()
        node2.start()
        
        time.sleep(0.5)
        
        # Connect nodes
        node2.connect_to_peer('localhost', 5210)
        
        time.sleep(0.5)
        
        # Store a file on node1
        test_file = os.path.join(self.temp_dir, "test_dist.txt")
        with open(test_file, 'w') as f:
            f.write("Distributed content")
        
        file_hash = node1.store_file(test_file)
        
        time.sleep(0.5)
        
        # Retrieve from node2 (should get it from node1)
        content = node2.retrieve_file(file_hash)
        
        self.assertIsNotNone(content)
        self.assertEqual(content, "Distributed content")


if __name__ == '__main__':
    unittest.main()
