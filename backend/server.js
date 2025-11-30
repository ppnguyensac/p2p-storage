const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");
const { Web3 } = require("web3");
const axios = require("axios");
const FormData = require("form-data");
const CryptoJS = require("crypto-js");

const app = express();
app.use(cors());
app.use(express.json()); // parse JSON bodies

// where uploaded files temporarily live
const upload = multer({ dest: path.join(__dirname, "uploads") });

// serve frontend UI (if you have a public/ folder)
const publicDir = path.join(__dirname, "public");
if (fs.existsSync(publicDir)) {
  app.use(express.static(publicDir));
}

// ---------------- Web3 + contract setup ----------------

const web3 = new Web3("http://127.0.0.1:8545"); // ganache-cli RPC

// adjust path if needed
const StorageRegistryJson = require("../build/contracts/StorageRegistry.json");

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

// test, change and put in .env if needed
const AES_SECRET = process.env.AES_SECRET || "CHANGE_ME_SUPER_SECRET_PASSPHRASE";

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

// ---------------- Helper: Encryption / Decryption ----------------

function encryptBuffer(buffer) {
  // encrypt base64-encoded plaintext
  const plaintextBase64 = buffer.toString("base64");
  const ciphertext = CryptoJS.AES.encrypt(plaintextBase64, AES_SECRET).toString();
  return Buffer.from(ciphertext, "utf8");
}

function decryptBuffer(encryptedBuffer) {
  const ciphertext = encryptedBuffer.toString("utf8");
  const bytes = CryptoJS.AES.decrypt(ciphertext, AES_SECRET);
  const plaintextBase64 = bytes.toString(CryptoJS.enc.Utf8);
  if (!plaintextBase64) {
    throw new Error("Decryption failed (empty plaintext)");
  }
  return Buffer.from(plaintextBase64, "base64");
}

function normalizeFileId(fileId) {
  if (!fileId.startsWith("0x")) {
    throw new Error("fileId must start with 0x");
  }
  if (fileId.length !== 66) {
    throw new Error("fileId must be 32 bytes (0x + 64 hex chars)");
  }
  return fileId.toLowerCase();
}


// ---------------- Helper: Node health / registry helpers ----------------

async function pickHealthyNode() {
  for (const node of nodes) {
    try {
      await axios.get(`${node.url}/health`, { timeout: 1000 });
      return node;
    } catch (e) {
      console.warn("Node unhealthy:", node.url, "-", e.message);
    }
  }
  throw new Error("No healthy storage nodes available");
}

async function getNodeInfoFromRegistry(nodeId) {
  const ans = await registry.methods.getNode(nodeId).call();
  return { active: ans[0], url: ans[1] };
}

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

// backend health
app.get("/health", (req, res) => {
  res.json({ ok: true });
});

// Real-time node health check
app.get("/nodes/status", async (req, res) => {
  try {
    const now = new Date().toISOString();
    const results = [];

    for (const node of nodes) {
      const start = Date.now();
      try {
        const response = await axios.get(`${node.url}/health`, {
          timeout: 1000, // 1 second timeout
        });
        const latency = Date.now() - start;

        results.push({
          nodeId: node.nodeId,
          url: node.url,
          online: true,
          latencyMs: latency,
          lastChecked: now,
          healthPayload: response.data,
        });
      } catch (err) {
        results.push({
          nodeId: node.nodeId,
          url: node.url,
          online: false,
          latencyMs: null,
          lastChecked: now,
          error: err.message,
        });
      }
    }

    res.json({
      checkedAt: now,
      nodes: results,
    });
  } catch (err) {
    console.error("NODE STATUS ERROR:", err);
    res.status(500).json({ error: err.message });
  }
});

// Upload a file: expects form-data with `owner` (eth address) and `file`
// Optional: `signature` from MetaMask signing the message "Upload file {fileId} as owner {owner}"
app.post("/upload", upload.single("file"), async (req, res) => {
  let filePath;
  let encPath;
  try {
    const owner = (req.body.owner || "").trim();
    const signature = req.body.signature || null;

    if (!owner) {
      return res.status(400).json({
        error: "Owner address is required.",
        code: "MISSING_OWNER",
      });
    }

    if (!req.file) {
      return res.status(400).json({
        error: "You must select a file to upload.",
        code: "MISSING_FILE",
      });
    }

    // Make sure owner is one of the Ganache accounts
    const accounts = await web3.eth.getAccounts();
    if (!accounts.map(a => a.toLowerCase()).includes(owner.toLowerCase())) {
      return res.status(400).json({
        error:
          "Owner address must be one of the Ganache accounts shown in ganache-cli.",
        code: "INVALID_OWNER",
      });
    }

    filePath = req.file.path;
    const rawBuffer = fs.readFileSync(filePath);
    const size = rawBuffer.length;

    // keccak256(original plaintext bytes)
    const fileHash = web3.utils.keccak256(
      "0x" + rawBuffer.toString("hex")
    );

    // fileId = keccak256(fileHash + owner)
    const fileId = web3.utils.keccak256(
      web3.utils.encodePacked(fileHash, owner)
    );

    console.log("Upload:");
    console.log(" owner:", owner);
    console.log(" fileHash:", fileHash);
    console.log(" fileId:", fileId);

    // Optional: MetaMask signature verification
    if (signature) {
      try {
        const message = `Upload file ${fileId} as owner ${owner}`;
        const recovered = await web3.eth.accounts.recover(message, signature);
        if (recovered.toLowerCase() !== owner.toLowerCase()) {
          return res.status(403).json({
            error: "Signature does not match owner address.",
            code: "INVALID_SIGNATURE",
          });
        }
        console.log("MetaMask signature verified for", owner);
      } catch (e) {
        console.error("SIGNATURE VERIFY ERROR:", e);
        return res.status(400).json({
          error: "Failed to verify signature.",
          code: "SIGNATURE_VERIFY_FAILED",
        });
      }
    }

    // Encrypt file contents before sending to nodes
    const encryptedBuffer = encryptBuffer(rawBuffer);
    encPath = filePath + ".enc";
    fs.writeFileSync(encPath, encryptedBuffer);

    // Check if this fileId is already registered to avoid revert
    try {
      const existing = await registry.methods.getFile(fileId).call();
      const existingOwner = existing[0];

      if (
        existingOwner &&
        existingOwner !== "0x0000000000000000000000000000000000000000"
      ) {
        return res.status(409).json({
          error:
            "This file is already registered on-chain for that owner address.",
          code: "FILE_ALREADY_REGISTERED",
          fileId,
        });
      }
    } catch (e) {
      console.log(
        "getFile pre-check error (likely not registered yet):",
        e.message
      );
    }

    // store encrypted file on each node HTTP server
    const successfulReplicas = [];

    for (const node of nodes) {
      const form = new FormData();
      form.append("fileId", fileId);
      form.append("file", fs.createReadStream(encPath));

      console.log("Storing encrypted file on node:", node.url);
      try {
        await axios.post(`${node.url}/store`, form, {
          headers: form.getHeaders(),
          maxBodyLength: Infinity,
          maxContentLength: Infinity,
        });
        successfulReplicas.push(node.nodeId);
      } catch (err) {
        console.error("NODE STORE ERROR:", node.url, err.message);
      }
    }

    if (successfulReplicas.length === 0) {
      return res.status(502).json({
        error: "Failed to store file on any storage node.",
        code: "NO_NODE_STORED",
      });
    }

    // register file on chain (owner is msg.sender)
    try {
      await registry.methods
        .registerFile(fileId, fileHash, size, successfulReplicas)
        .send({ from: owner, gas: 500000 });
    } catch (err) {
      console.error("REGISTERFILE REVERT:", err);

      let userError = "On-chain file registration reverted.";
      if (err && err.reason) {
        userError += " Reason: " + err.reason;
      }

      return res.status(500).json({
        error: userError,
        code: "ONCHAIN_REVERT",
      });
    }

    return res.json({
      ok: true,
      fileId,
      fileHash,
      size,
      replicas: successfulReplicas,
    });
  } catch (err) {
    console.error("UPLOAD ERROR:", err);
    return res.status(500).json({
      error: "Unexpected server error during upload.",
      code: "SERVER_ERROR",
    });
  } finally {
    // clean temp files
    if (filePath && fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
    if (encPath && fs.existsSync(encPath)) {
      fs.unlinkSync(encPath);
    }
  }
});

// GET /file/:fileId  (metadata)
app.get("/file/:fileId", async (req, res) => {
  try {
    let fileId = req.params.fileId;

    try {
      fileId = normalizeFileId(fileId);
    } catch (err) {
      return res.status(400).json({ error: err.message });
    }

    const result = await registry.methods.getFile(fileId).call();

    const owner = result[0];
    const fileHash = result[1];
    const size = Number(result[2]);
    const replicas = result[3];

    if (!owner || owner === "0x0000000000000000000000000000000000000000") {
      return res.status(404).json({ error: "File not found on-chain" });
    }

    res.json({ owner, fileHash, size, replicas });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /file/:fileId/nodes  (replica list)
app.get("/file/:fileId/nodes", async (req, res) => {
  try {
    let fileId = req.params.fileId;

    try {
      fileId = normalizeFileId(fileId);
    } catch (err) {
      return res.status(400).json({ error: err.message });
    }

    const result = await registry.methods.getFile(fileId).call();

    const owner = result[0];
    const fileHash = result[1];
    const size = Number(result[2]);
    const replicas = result[3];

    if (!owner || owner === "0x0000000000000000000000000000000000000000") {
      return res.status(404).json({ error: "File not found on-chain" });
    }

    const nodeInfos = [];

    for (const nodeId of replicas) {
      const nodeRes = await registry.methods.getNode(nodeId).call();
      nodeInfos.push({
        nodeId,
        active: nodeRes[0],
        url: nodeRes[1],
      });
    }

    res.json({ fileId, owner, fileHash, size, nodes: nodeInfos });

  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Set per-file settings (download limit) and forward to storage nodes
app.post("/file/:fileId/settings", async (req, res) => {
  try {
    const fileId = req.params.fileId;
    // downloadLimit: integer or null to clear
    const downloadLimit = req.body.downloadLimit == null ? null : Number(req.body.downloadLimit);

    if (downloadLimit !== null && (!Number.isInteger(downloadLimit) || downloadLimit < 1)) {
      return res.status(400).json({ ok: false, error: "downloadLimit must be a positive integer or null" });
    }

    // forward settings to each node
    for (const node of nodes) {
      await axios.post(`${node.url}/set-download-limit`, { fileId, downloadLimit }, { timeout: 3000 });
    }

    res.json({ ok: true });
  } catch (err) {
    console.error("SETTINGS ERROR:", err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

const PORT = 5000;



//Download route with automatic node fallback + decryption + hash check
app.get("/download/:fileId", async (req, res) => {
  try {
    const fileId = req.params.fileId;

    // read on-chain metadata
    const result = await registry.methods.getFile(fileId).call();
    const owner = result[0];
    const fileHash = result[1];
    const size = Number(result[2]);
    const replicas = result[3];

    if (
      !owner ||
      owner === "0x0000000000000000000000000000000000000000"
    ) {
      return res.status(404).json({ error: "File not found on-chain" });
    }

    if (!replicas || replicas.length === 0) {
      return res.status(500).json({ error: "No replicas recorded on-chain" });
    }

    // Try each replica node until one succeeds
    for (const nodeId of replicas) {
      try {
        const { active, url } = await getNodeInfoFromRegistry(nodeId);
        if (!active || !url) {
          console.warn("Node inactive or no URL for nodeId:", nodeId);
          continue;
        }

        console.log(`Trying node ${url} for file ${fileId}`);
        const response = await axios.get(`${url}/get/${fileId}`, {
          responseType: "arraybuffer",
          timeout: 5000,
        });

        const encryptedBuffer = Buffer.from(response.data);
        const originalBuffer = decryptBuffer(encryptedBuffer);

        // optional size check
        if (size && originalBuffer.length !== size) {
          console.warn(
            `Size mismatch from node ${url}. Expected ${size}, got ${originalBuffer.length}`
          );
          continue;
        }

        // optional hash check
        const computedHash = web3.utils.keccak256(
          "0x" + originalBuffer.toString("hex")
        );
        if (computedHash.toLowerCase() !== fileHash.toLowerCase()) {
          console.warn(
            `Hash mismatch from node ${url}. Expected ${fileHash}, got ${computedHash}`
          );
          continue;
        }

        // Success: stream file to client
        res.setHeader("Content-Type", "application/octet-stream");
        res.setHeader(
          "Content-Disposition",
          `attachment; filename="${fileId}.bin"`
        );
        return res.send(originalBuffer);
      } catch (e) {
        console.warn(
          `Failed to download/decrypt from node for file ${fileId}:`,
          e.message
        );
        // try next node
      }
    }

    // If we reach here, all nodes failed
    return res.status(502).json({
      error: "Failed to retrieve file from any storage node",
      code: "DOWNLOAD_FALLBACK_EXHAUSTED",
    });
  } catch (err) {
    console.error("DOWNLOAD ERROR:", err);
    res.status(500).json({
      error: "Unexpected server error during download.",
      code: "SERVER_ERROR",
    });
  }
});

// Generate registry.js for frontend
function writeRegistryFrontendFile(address) {
  const outPath = path.join(__dirname, "public", "registry.js");
  const abi = JSON.stringify(StorageRegistryJson.abi, null, 2);

  const js = `
    // Auto-generated StorageRegistry ABI + Address
    const registryAbi = ${abi};
    const registryAddress = "${address}";
  `;

  fs.writeFileSync(outPath, js, "utf8");
  console.log("✔ wrote public/registry.js");
}

// call it once after contract loaded
writeRegistryFrontendFile(contractAddress);


// ---------------- Start server after init ----------------

const PORT = process.env.PORT || 5000;

async function start() {
  await init();
  app.listen(PORT, () => {
    console.log("Coordinator backend listening on port", PORT);
  });
}

start().catch((err) => {
  console.error("Fatal error starting backend:", err);
});
