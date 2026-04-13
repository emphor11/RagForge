# Local Deep Verify

Deep Verify now runs through a local verifier service on the user's machine.

## What it does

- The hosted app performs the normal Fast Review pass.
- When the user clicks `Run Deep Verify`, the browser calls a local service at `http://127.0.0.1:11435`.
- That local service talks to the user's own Ollama runtime.
- The local service writes the enriched audit back into the hosted backend.

## Start Ollama

Make sure Ollama is installed and running locally:

```bash
ollama serve
ollama pull llama3.1:8b
```

## Start the local verifier

From this repo:

```bash
uvicorn app.local_verify_service:app --host 127.0.0.1 --port 11435
```

Optional environment variables:

```bash
export OLLAMA_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=llama3.1:8b
```

For slower local machines, you can allow longer verification runs or send less raw text to Ollama:

```bash
export OLLAMA_TIMEOUT_SECONDS=420
export OLLAMA_MAX_RAW_CHARS=14000
```

If Deep Verify still feels slow, try a smaller model such as:

```bash
export OLLAMA_MODEL=qwen2.5:7b
```

If your Python installation has local certificate issues when calling the hosted backend over HTTPS, you can temporarily disable backend certificate verification for the local verifier only:

```bash
export VERIFY_BACKEND_SSL=false
```

Use that only for troubleshooting on your own machine. The default is `true`.

## Result

Once both Ollama and the local verifier are running, the hosted UI can trigger Deep Verify and store the updated review audit back into the hosted document record.
