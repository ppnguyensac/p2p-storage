const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const { Web3 } = require("web3");
const axios = require("axios");
const FormData = require("form-data");

const app = express();
app.use(cors());
app.use(express.json());

const upload = multer({ dest: path.join(__dirname, "uploads") });

// IMPORT NEW
const publicDir = path.join(__dirname, "public");
app.use(express.static(publicDir));

// ---------------- Web3 + contract setup ----------------

const web3 = new Web3("http://127.0.0.1:8545"); // ganache-cli RPC

const StorageRegistryJson = require("../build/contracts/StorageRegistry.json");

// Use the MOST RECENT deployed network (last key)
const networks = StorageRegistryJson.networks;
const networkIds = Object.keys(networks);

if (networkIds.length === 0) {
  throw new Error("StorageRegistry is not deployed on any network.");
}

const lastNetworkId = networkIds[networkIds.length - 1];
const contractAddress = networks[lastNetworkId].address;

console.log("Using StorageRegistry network:", lastNetworkId);
console.log("Using StorageRegistry at:", contractAddress);

const registry = new web3.eth.Contract(
  StorageRegistryJson.abi,
  contractAddress
);

let adminAccount;

// local storage nodes we simulate
const nodes = [
  {
    nodeId: web3.utils.keccak256("node1"),
    url: "http://localhost:4001",
  },
  {
    nodeId: web3.utils.keccak256("node2"),
    url: "http://localhost:4002",
  },
];

// Register nodes on-chain at startup
async function init() {
  const accounts = await web3.eth.getAccounts();
  adminAccount = accounts[0];
  console.log("Using admin account:", adminAccount);

  for (const n of nodes) {
    console.log("Registering node on chain:", n.nodeId, n.url);
    await registry.methods
      .registerNode(n.nodeId, n.url)
      .send({ from: adminAccount, gas: 300000 });
  }

  console.log("Nodes registered on chain");
}

// ---------------- Routes ----------------

app.get("/health", (req, res) => {
  res.json({ ok: true });
});

// Upload a file: expects form-data with `owner` (eth address) and `file`
app.post("/upload", upload.single("file"), async (req, res) => {
  try {
    const owner = req.body.owner;

    if (!owner) {
      return res.status(400).json({ error: "owner (address) required" });
    }
    if (!req.file) {
      return res.status(400).json({ error: "file required" });
    }

    const filePath = req.file.path;
    const fileBuffer = fs.readFileSync(filePath);
    const size = fileBuffer.length;

    // keccak256(file bytes)
    const fileHash = web3.utils.keccak256(
      "0x" + fileBuffer.toString("hex")
    );

    // fileId = keccak256(fileHash + owner)
    const fileId = web3.utils.keccak256(
      web3.utils.encodePacked(fileHash, owner)
    );

    console.log("Upload:");
    console.log(" owner:", owner);
    console.log(" fileHash:", fileHash);
    console.log(" fileId:", fileId);

    const replicas = nodes.map((n) => n.nodeId);

    // store file on each node HTTP server
    for (const node of nodes) {
      const form = new FormData();
      form.append("fileId", fileId);
      form.append("file", fs.createReadStream(filePath));

      console.log("Storing file on node:", node.url);
      await axios.post(`${node.url}/store`, form, {
        headers: form.getHeaders(),
      });
    }

    // register file on chain (owner is msg.sender)
    await registry.methods
      .registerFile(fileId, fileHash, size, replicas)
      .send({ from: owner, gas: 500000 });

    res.json({ ok: true, fileId, fileHash, size, replicas });
  } catch (err) {
    console.error("UPLOAD ERROR:", err);
    res.status(500).json({ error: err.message });
  }
});

// Get on-chain metadata for a file
app.get("/file/:fileId", async (req, res) => {
  try {
    const fileId = req.params.fileId;
    const result = await registry.methods.getFile(fileId).call();

    const owner = result[0];
    const fileHash = result[1];
    const size = Number(result[2]);   // BigInt -> Number
    const replicas = result[3];

    res.json({ owner, fileHash, size, replicas });
  } catch (err) {
    console.error("GET FILE ERROR:", err);
    res.status(500).json({ error: err.message });
  }
});

// Get node info (URLs + active) for a file
app.get("/file/:fileId/nodes", async (req, res) => {
  try {
    const fileId = req.params.fileId;

    const result = await registry.methods.getFile(fileId).call();
    const owner = result[0];
    const fileHash = result[1];
    const size = Number(result[2]);   // BigInt -> Number
    const replicas = result[3];

    const nodeInfos = [];
    for (const nodeId of replicas) {
      const nodeRes = await registry.methods.getNode(nodeId).call();
      const active = nodeRes[0];
      const url = nodeRes[1];
      nodeInfos.push({ nodeId, active, url });
    }

    res.json({ fileId, owner, fileHash, size, nodes: nodeInfos });
  } catch (err) {
    console.error("GET FILE NODES ERROR:", err);
    res.status(500).json({ error: err.message });
  }
});

const PORT = 5000;

// Start ONLY after init() finishes, so nodes are registered first
async function start() {
  await init();
  app.listen(PORT, () => {
    console.log("Coordinator backend listening on port", PORT);
  });
}

start().catch((err) => {
  console.error("Fatal error starting backend:", err);
});

