# RUBY — Troubleshooting & Diagnostics Guide

This document outlines solutions for common setup, runtime, hardware, and operational scenarios.

---

## 1. Local AI & Ollama Issues

### Issue: Ollama daemon shows as "Offline" in Analytics/Providers
**Cause:** The local Ollama service is not running or is bound to a different port.
**Resolution:**
1. Check if Ollama service is active:
   ```bash
   ollama list
   ```
2. Start Ollama in the background:
   ```bash
   ollama serve > /dev/null 2>&1 &
   ```
3. Test connection:
   ```bash
   curl http://127.0.0.1:11434/api/tags
   ```

### Issue: GPU VRAM Out-of-Memory (OOM) during Local Inference
**Cause:** Model parameter count exceeds available GPU VRAM (e.g. attempting to load 14B or 70B models on a 6GB RTX 3050).
**Resolution:**
1. Check available VRAM in **Analytics -> Hardware Telemetry** or via `nvidia-smi`.
2. Use 4-bit quantized 3B to 8B models:
   ```bash
   ollama pull llama3.2:3b
   ollama pull qwen2.5:7b
   ```
3. Use the **Model VRAM Capacity Evaluator** in the Analytics page to verify compatibility before downloading.

---

## 2. Secrets Management & Linux Keyring

### Issue: "Secret service / Keyring locked or unavailable"
**Cause:** Headless Linux environments (e.g., SSH sessions, cron jobs, minimal containers) without an unlocked DBus desktop session (`gnome-keyring`, `kwallet`).
**Resolution:**
- RUBY includes an automatic, transparent fallback: when Linux Keyring is unavailable, it automatically switches to a local salted AES-256-GCM encrypted file store (`data/.secrets.enc`).
- You do not need to configure anything manually. Secrets remain encrypted at rest.

---

## 3. Document Ingestion & Parsers

### Issue: Legacy `.doc` or `.ppt` files fail to parse
**Cause:** Legacy binary formats require LibreOffice on the host system for headless PDF conversion.
**Resolution:**
1. Install LibreOffice:
   ```bash
   # Debian / Ubuntu
   sudo apt-get install -y libreoffice-core libreoffice-writer libreoffice-impress

   # Fedora / RHEL
   sudo dnf install -y libreoffice-core libreoffice-writer libreoffice-impress
   ```
2. Alternatively, save your document in modern OpenXML formats (`.docx`, `.pptx`) before uploading.

### Issue: Scanned PDF or Image OCR returns low or empty text
**Cause:** Tesseract OCR engine or poppler utilities are missing from the host environment.
**Resolution:**
```bash
# Debian / Ubuntu
sudo apt-get install -y tesseract-ocr poppler-utils

# Fedora
sudo dnf install -y tesseract poppler-utils
```

---

## 4. Academic Simulators & Math Engine

### Issue: SymPy reports SyntaxError on complex formulas
**Cause:** Standard programming operators must be used for algebraic input:
- Use `**` for exponentiation (e.g., `x**2 + 5*x`, NOT `x^2`).
- Explicitly write multiplication operators (e.g., `2*x`, NOT `2x`).
- Trigonometric functions require parentheses: `sin(x)*cos(x)`.

### Issue: Code execution in DSA workspace fails with "Security Exception"
**Cause:** The restricted code sandbox statically blocks imports and functions that interact with the host system (`os`, `sys`, `subprocess`, `socket`, `open`, `eval`, and reflection attributes).
**Resolution:**
- Academic dry-runs must be self-contained algorithms using pure Python primitives, math, collections, and standard algorithms.

---

## 5. Port Conflicts & Server Management

### Issue: Server fails to start: "Address already in use: 127.0.0.1:8000"
**Cause:** Another process or a previous Ruby instance is still occupying port 8000.
**Resolution:**
1. Stop the existing Ruby instance:
   ```bash
   ./stop.sh
   ```
2. If another process is holding the port, identify and terminate it:
   ```bash
   lsof -i :8000
   kill -9 <PID>
   ```

### Issue: Front-end route gives 404 after direct browser refresh
**Cause:** Frontend production assets were not built.
**Resolution:**
```bash
cd frontend && npm run build && cd ..
./start.sh
```

---

## 6. Backups & Restoration

### Issue: `restore.sh` fails with "Ruby is currently running"
**Cause:** Safety guard prevents overwriting database files while the server is active.
**Resolution:**
1. Run `./stop.sh` before restoring.
2. If you are confident the process ID is stale, pass `--force`:
   ```bash
   ./scripts/restore.sh backups/ruby_backup_<timestamp>.tar.gz --force
   ```
