// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract StorageRegistry {

    struct StorageNode {
        bool active;
        string url;
    }

    struct FileRecord {
        address owner;
        bytes32 fileHash;
        uint256 size;
        bytes32[] replicas;
    }

    // nodeId → node info
    mapping(bytes32 => StorageNode) public nodes;

    // fileId → FileRecord
    mapping(bytes32 => FileRecord) public files;

    event NodeRegistered(bytes32 indexed nodeId, string url);
    event NodeStatusChanged(bytes32 indexed nodeId, bool active);
    event FileRegistered(
        bytes32 indexed fileId,
        address indexed owner,
        bytes32 fileHash,
        uint256 size
    );
    event ReplicasUpdated(bytes32 indexed fileId, bytes32[] replicas);

    // Register a storage node
    function registerNode(bytes32 nodeId, string calldata url) external {
        nodes[nodeId] = StorageNode({ active: true, url: url });
        emit NodeRegistered(nodeId, url);
    }

    function setNodeActive(bytes32 nodeId, bool active) external {
        nodes[nodeId].active = active;
        emit NodeStatusChanged(nodeId, active);
    }

    // Register file on-chain
    function registerFile(
        bytes32 fileId,
        bytes32 fileHash,
        uint256 size,
        bytes32[] calldata replicas
    ) external {
        require(files[fileId].owner == address(0), "File already registered");

        files[fileId].owner = msg.sender;
        files[fileId].fileHash = fileHash;
        files[fileId].size = size;

        for (uint i = 0; i < replicas.length; i++) {
            files[fileId].replicas.push(replicas[i]);
        }

        emit FileRegistered(fileId, msg.sender, fileHash, size);
        emit ReplicasUpdated(fileId, replicas);
    }

    // Read file info
    function getFile(bytes32 fileId)
        external
        view
        returns (
            address owner,
            bytes32 fileHash,
            uint256 size,
            bytes32[] memory replicas
        )
    {
        FileRecord storage f = files[fileId];
        return (f.owner, f.fileHash, f.size, f.replicas);
    }

    // Read node info
    function getNode(bytes32 nodeId)
        external
        view
        returns (bool active, string memory url)
    {
        StorageNode storage n = nodes[nodeId];
        return (n.active, n.url);
    }
}
