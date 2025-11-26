const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(cors());
app.use(express.json()); // parse JSON for settings endpoint

const storageDir = path.join(__dirname, "data");
if (!fs.existsSync(storageDir)) fs.mkdirSync(storageDir);

const upload = multer({ dest: storageDir });

app.get("/health", (req, res) => {
  res.json({ ok: true, node: "node1" });
});

app.post("/store", upload.single("file"), (req, res) => {
  const fileId = req.body.fileId;
  if (!fileId || !req.file) {
    return res.status(400).json({ error: "fileId and file required" });
  }

  const targetPath = path.join(storageDir, fileId);
  fs.renameSync(req.file.path, targetPath);

  // clear any existing metadata when the file is (re)stored
  const metaPath = path.join(storageDir, fileId + ".meta.json");
  if (fs.existsSync(metaPath)) fs.unlinkSync(metaPath);

  res.json({ ok: true, node: "node1", storedAs: fileId });
});

// set download limit metadata for a file
app.post("/set-download-limit", (req, res) => {
  const { fileId, downloadLimit } = req.body;
  if (!fileId) return res.status(400).json({ error: "fileId required" });

  const metaPath = path.join(storageDir, fileId + ".meta.json");

  if (downloadLimit == null) {
    // clear limit
    if (fs.existsSync(metaPath)) fs.unlinkSync(metaPath);
    return res.json({ ok: true, cleared: true });
  }

  const meta = {
    limit: Number(downloadLimit),
    remaining: Number(downloadLimit),
  };

  fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2));
  return res.json({ ok: true, meta });
});

app.get("/get/:fileId", (req, res) => {
  const filePath = path.join(storageDir, req.params.fileId);
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: "not found" });
  }

  const metaPath = path.join(storageDir, req.params.fileId + ".meta.json");
  if (fs.existsSync(metaPath)) {
    try {
      const raw = fs.readFileSync(metaPath, "utf8");
      const meta = JSON.parse(raw);

      if (typeof meta.remaining === "number") {
        if (meta.remaining <= 0) {
          // once limit reached return an error status
          return res.status(410).json({ error: "download limit reached" });
        }

        // decrement remaining and persist before sending file
        meta.remaining = meta.remaining - 1;
        fs.writeFileSync(metaPath, JSON.stringify(meta, null, 2));
      }
    } catch (e) {
      console.error("meta read/write error:", e);
      // continue and serve file if metadata is corrupted
    }
  }

  res.sendFile(filePath);
});

const PORT = 4001;
app.listen(PORT, () => {
  console.log("Storage node1 listening on port", PORT);
});

