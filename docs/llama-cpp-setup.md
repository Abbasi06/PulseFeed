# llama.cpp Server Setup

Three llama.cpp servers replace the Gemini API. Each is optimised for a specific
task tier. Total RAM: ~4.1 GB — comfortable on a 16 GB laptop.

| Port | Model | Task | RAM |
|------|-------|------|-----|
| 8080 | gemma3-1b | Gatekeeper (binary signal filter), Validator (feed scoring) | ~1.0 GB |
| 8081 | gemma3-4b | Extractor (structured JSON extraction) | ~2.8 GB |
| 8082 | nomic-embed-text | Embeddings (vector search) | ~0.3 GB |

---

## 1. Install llama.cpp

Download the latest release for your platform from:
https://github.com/ggerganov/llama.cpp/releases

Extract and add `llama-server` (or `llama-server.exe` on Windows) to your PATH,
or note the full path to the binary.

---

## 2. Download model files (GGUF)

Create a `models/` directory anywhere convenient (e.g. `C:\llama-models\`).

**gemma3-1b** (~1.0 GB):
```
https://huggingface.co/bartowski/google_gemma-3-1b-it-GGUF
→ google_gemma-3-1b-it-Q4_K_M.gguf
```

**gemma3-4b** (~2.8 GB):
```
https://huggingface.co/bartowski/google_gemma-3-4b-it-GGUF
→ google_gemma-3-4b-it-Q4_K_M.gguf
```

**nomic-embed-text** (~0.3 GB):
```
https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF
→ nomic-embed-text-v1.5.Q8_0.gguf
```

---

## 3. Start the servers

Open three terminal windows (or use Windows Task Scheduler / startup scripts).

**Port 8080 — Light model (gatekeeper + validator):**
```bash
llama-server \
  --model C:\llama-models\google_gemma-3-1b-it-Q4_K_M.gguf \
  --port 8080 \
  --ctx-size 4096 \
  --threads 4 \
  --host 0.0.0.0
```

**Port 8081 — Heavy model (extractor):**
```bash
llama-server \
  --model C:\llama-models\google_gemma-3-4b-it-Q4_K_M.gguf \
  --port 8081 \
  --ctx-size 8192 \
  --threads 6 \
  --host 0.0.0.0
```

**Port 8082 — Embedding model:**
```bash
llama-server \
  --model C:\llama-models\nomic-embed-text-v1.5.Q8_0.gguf \
  --port 8082 \
  --ctx-size 2048 \
  --threads 4 \
  --host 0.0.0.0 \
  --embeddings \
  --pooling mean
```

---

## 4. Auto-start on Windows boot (optional but recommended)

Create a batch file `start-llama-servers.bat`:

```batch
@echo off
start "llama-light" llama-server --model C:\llama-models\google_gemma-3-1b-it-Q4_K_M.gguf --port 8080 --ctx-size 4096 --threads 4 --host 0.0.0.0
start "llama-heavy" llama-server --model C:\llama-models\google_gemma-3-4b-it-Q4_K_M.gguf --port 8081 --ctx-size 8192 --threads 6 --host 0.0.0.0
start "llama-embed" llama-server --model C:\llama-models\nomic-embed-text-v1.5.Q8_0.gguf --port 8082 --ctx-size 2048 --threads 4 --host 0.0.0.0 --embeddings --pooling mean
```

Place a shortcut to this file in:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

Windows will run it on every boot — no manual management needed.

---

## 5. Verify

```bash
# Test light model
curl http://localhost:8080/health

# Test heavy model
curl http://localhost:8081/health

# Test embeddings
curl http://localhost:8082/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "input": "hello world"}'
```

---

## Harvest schedule

PulseGen runs in batch mode — **06:00 and 18:00 UTC daily**.
The heavy model server (port 8081) is only under load for ~10-20 minutes
during those windows. All three servers combined use ~4.1 GB RAM at peak,
leaving ~12 GB free for everything else on a 16 GB machine.

To override the model for any tier, set environment variables in `.env`:
```
LLM_LIGHT_URL=http://host.docker.internal:8080/v1
LLM_HEAVY_URL=http://host.docker.internal:8081/v1
LLM_EMBED_URL=http://host.docker.internal:8082/v1
LLM_API_KEY=local
```
