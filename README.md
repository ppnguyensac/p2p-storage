# P2P Storage Network

A decentralized peer-to-peer (P2P) storage system that allows users to store and retrieve files across a distributed network of nodes.

## Features

- **Decentralized Architecture**: No central server - all nodes are equal peers
- **Distributed Hash Table (DHT)**: Efficient file discovery across the network
- **Data Replication**: Files are automatically replicated across multiple nodes for redundancy
- **Content Addressing**: Files are identified by their cryptographic hash (SHA-256)
- **Network Communication**: Nodes can connect to each other and form a mesh network
- **Simple CLI**: Easy-to-use command-line interface for all operations

## Architecture

### Components

1. **DHTNode**: Implements a Distributed Hash Table for file discovery
   - Maintains a routing table of known peers
   - Stores file hash to location mappings
   - Finds the closest node for a given key

2. **P2PStorageNode**: Main node implementation
   - Handles network communication with other peers
   - Stores and retrieves files locally
   - Replicates files to connected peers
   - Processes requests from other nodes

3. **CLI Interface**: Command-line tool for interacting with the network
   - Start nodes and join the network
   - Store and retrieve files
   - Monitor network status

## Installation

No external dependencies required! The system uses only Python standard library.

```bash
git clone https://github.com/ppnguyensac/p2p-storage.git
cd p2p-storage
```

Requirements:
- Python 3.6 or higher

## Usage

### Starting a Node

Start the first node in the network:

```bash
python3 p2p_cli.py start --host localhost --port 5000
```

Start additional nodes and connect to the network:

```bash
# In a new terminal
python3 p2p_cli.py start --host localhost --port 5001 --connect localhost:5000

# In another terminal
python3 p2p_cli.py start --host localhost --port 5002 --connect localhost:5001
```

### Interactive Commands

Once a node is running, you can use these interactive commands:

- `status` - Show network status (peers, files, node info)
- `list` - List all files stored on this node
- `quit` - Stop the node and exit

### Storing Files

Store a file in the network:

```bash
python3 p2p_cli.py store myfile.txt --connect localhost:5000
```

The command will output the file's hash, which you need to retrieve it later.

### Retrieving Files

Retrieve a file using its hash:

```bash
python3 p2p_cli.py retrieve <file_hash> -o output.txt --connect localhost:5000
```

### Listing Files

List all files stored on a node:

```bash
python3 p2p_cli.py list --connect localhost:5000
```

### Checking Node Status

Check if a node is online:

```bash
python3 p2p_cli.py status --connect localhost:5000
```

## Example Workflow

Here's a complete example of using the P2P storage system:

```bash
# Terminal 1: Start first node
python3 p2p_cli.py start --host localhost --port 5000

# Terminal 2: Start second node and connect
python3 p2p_cli.py start --host localhost --port 5001 --connect localhost:5000

# Terminal 3: Store a file
echo "Hello, P2P World!" > test.txt
python3 p2p_cli.py store test.txt --connect localhost:5000
# Output: File hash: abc123...

# Terminal 3: Retrieve the file from any node
python3 p2p_cli.py retrieve abc123... -o retrieved.txt --connect localhost:5001
cat retrieved.txt
# Output: Hello, P2P World!
```

## How It Works

### File Storage Process

1. When you store a file, the node:
   - Calculates the SHA-256 hash of the file content
   - Stores the file locally using the hash as the filename
   - Updates its DHT with the file hash
   - Replicates the file to all connected peers

2. Files are stored in a `node_data_<node_id>` directory

### File Retrieval Process

1. When you retrieve a file:
   - The node first checks its local storage
   - If not found locally, it queries connected peers
   - Once found, the file is cached locally for future requests

### Network Protocol

Nodes communicate using JSON messages over TCP sockets. Supported actions:

- `PING`: Check if a node is online
- `STORE`: Store a file on the node
- `RETRIEVE`: Retrieve a file from the node
- `JOIN`: Register as a peer in the network
- `LIST`: List all files on the node

## Testing

Run the comprehensive test suite:

```bash
python3 -m unittest test_p2p_storage.py -v
```

The test suite includes:
- Unit tests for DHT functionality
- Unit tests for node operations
- Integration tests for multi-node networks
- File replication tests

## Architecture Decisions

### Why DHT?

The Distributed Hash Table provides efficient O(log n) lookup times for file discovery without requiring a central index.

### Why Content Addressing?

Using cryptographic hashes (SHA-256) as file identifiers ensures:
- Content verification (files can't be tampered with)
- Deduplication (identical files have the same hash)
- Location independence (files can move between nodes)

### Why TCP?

TCP provides reliable, ordered delivery which is important for file transfers and ensures data integrity.

## Limitations and Future Enhancements

Current limitations:
- No authentication or encryption (files are transmitted in plain text)
- Simple replication strategy (replicates to all peers)
- No automatic peer discovery (must manually connect to known peers)
- Files are stored as text only

Potential enhancements:
- Add encryption for secure file storage and transmission
- Implement NAT traversal for internet-wide P2P networks
- Add peer discovery mechanism (DHT bootstrapping)
- Support binary files
- Implement erasure coding for efficient redundancy
- Add file versioning and conflict resolution
- Implement bandwidth-aware routing

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License - See LICENSE file for details

## References

- [Kademlia DHT](https://en.wikipedia.org/wiki/Kademlia)
- [IPFS](https://ipfs.io/)
- [BitTorrent Protocol](https://www.bittorrent.org/beps/bep_0003.html)