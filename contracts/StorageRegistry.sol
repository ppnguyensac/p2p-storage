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
        bytes32[] replicas; // nodeIds
    }

    // nodeId => node info (nodeId is bytes32)
    mapping(bytes32 => StorageNode) public nodes;

    // fileId => record
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

    // ---- Node management ----

    function registerNode(bytes32 nodeId, string calldata url) external {
        nodes[nodeId] = StorageNode({ active: true, url: url });
        emit NodeRegistered(nodeId, url);
    }

    function setNodeActive(bytes32 nodeId, bool active) external {
        require(bytes(nodes[nodeId].url).length > 0, "Node not registered");
        nodes[nodeId].active = active;
        emit NodeStatusChanged(nodeId, active);
    }

    // ---- File management ----

    function registerFile(
        bytes32 fileId,
        bytes32 fileHash,
        uint256 size,
        bytes32[] calldata replicas
    ) external {
        require(files[fileId].owner == address(0), "File exists");
        require(replicas.length > 0, "Need replicas");

        FileRecord storage f = files[fileId];
        f.owner = msg.sender;
        f.fileHash = fileHash;
        f.size = size;

        for (uint i = 0; i < replicas.length; i++) {
            require(bytes(nodes[replicas[i]].url).length > 0, "Unknown node");
            f.replicas.push(replicas[i]);
        }

        emit FileRegistered(fileId, msg.sender, fileHash, size);
        emit ReplicasUpdated(fileId, replicas);
    }

    function updateReplicas(
        bytes32 fileId,
        bytes32[] calldata newReplicas
    ) external {
        FileRecord storage f = files[fileId];
        require(f.owner == msg.sender, "Not file owner");
        require(newReplicas.length > 0, "Need replicas");

        delete f.replicas;
        for (uint i = 0; i < newReplicas.length; i++) {
            require(bytes(nodes[newReplicas[i]].url).length > 0, "Unknown node");
            f.replicas.push(newReplicas[i]);
        }

        emit ReplicasUpdated(fileId, newReplicas);
    }

    function getFile(bytes32 fileId)
        external
        view
        returns (address, bytes32, uint256, bytes32[] memory)
    {
        FileRecord storage f = files[fileId];
        return (f.owner, f.fileHash, f.size, f.replicas);
    }

    function getNode(bytes32 nodeId)
        external
        view
        returns (bool, string memory)
    {
        StorageNode storage n = nodes[nodeId];
        return (n.active, n.url);
    }
}

