const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");

const app = express();
app.use(cors());

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

  res.json({ ok: true, node: "node1", storedAs: fileId });
});

app.get("/get/:fileId", (req, res) => {
  const filePath = path.join(storageDir, req.params.fileId);
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: "not found" });
  }
  res.setHeader("Content-Type", "application/octet-stream");
  res.sendFile(filePath);
});

const PORT = 4001;
app.listen(PORT, () => {
  console.log("Storage node1 listening on port", PORT);
});
