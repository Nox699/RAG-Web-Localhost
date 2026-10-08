# Local RAG Web — localhost med Ollama

En webbaseret videreudvikling af undervisningsprojektet. Løsningen kører som standard **kun på `127.0.0.1`**, bruger lokale Ollama-modeller og har dokumentstyring, persistent indeks og historik i tekstfiler.

## Funktioner

- Webinterface til spørgsmål/svar og retrieved evidence.
- Upload og fjern dokumenter fra browseren.
- Understøtter `.txt`, `.md`, `.csv`, `.json`, `.log`, `.pdf` og `.docx`.
- Automatisk genindeksering efter upload og manuel **Genbyg hele indeks**.
- Persistent SQLite-indeks i `state/rag.sqlite3`, så embeddings kan genbruges efter genstart, så længe dokumenter og embeddingmodel er uændrede.
- `logs/qa_history.txt`: spørgsmål + svar + kilder.
- `logs/evidence_history.txt`: spørgsmål + de chunks/similarity-scores der blev hentet.
- Begge logs kan ses, downloades og ryddes fra webinterfacet.
- Uploadgrænse, filtypekontrol, sikre filnavne, atomisk batch-upload og stale-index-kontrol.
- Ingen CDN'er eller eksterne frontend-assets.
- Binder kun til localhost som standard.

## 1. Forudsætninger

- Python 3.11+ anbefales.
- Ollama installeret og kørende lokalt.

Download modellerne:

```bash
ollama pull embeddinggemma
ollama pull qwen3:1.7b
```

Sørg for at Ollama kører:

```bash
ollama serve
```

> På systemer hvor Ollama allerede kører som service, skal `ollama serve` ikke startes en ekstra gang.

## 2. Installer

### Linux/macOS

```bash
cd RAG_Web_Localhost
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
cd RAG_Web_Localhost
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Start webappen

```bash
python run.py
```

Åbn derefter:

```text
http://127.0.0.1:8000
```

De tre medfølgende `.txt`-filer ligger i `data/`. Første gang skal indekset bygges. Klik **Dokumenter → Genbyg hele indeks**.

## 4. Typisk workflow

1. Åbn **Dokumenter**.
2. Upload en eller flere filer. Appen forsøger automatisk at genbygge indekset.
3. Gå til **Chat** og stil et spørgsmål.
4. Se både svar og retrieved evidence med similarity-score.
5. Gå til **Logfiler** for at se eller downloade historikken.
6. Fjern dokumenter fra dokumentlisten. De tilhørende chunks fjernes også fra SQLite-indekset.

## Mapper og data

```text
app/                    FastAPI + frontend
  core.py               RAG, dokumentudtræk, embeddings, retrieval, logs
  main.py               HTTP API
  static/                HTML/CSS/JavaScript
data/                    Dokumenter der må indgå i RAG
logs/
  qa_history.txt         Spørgsmål + svar
  evidence_history.txt   Spørgsmål + retrieved evidence
state/
  rag.sqlite3            Persistent embeddings/chunks
run.py                   Lokal startfil
tests/                   Offline tests + localhost smoke-server
```

## API

Når serveren kører, findes FastAPI-dokumentationen på:

```text
http://127.0.0.1:8000/api/docs
```

Vigtige endpoints:

- `GET /api/status`
- `GET /api/documents`
- `POST /api/documents`
- `DELETE /api/documents/{filename}`
- `POST /api/index/rebuild`
- `POST /api/ask`
- `GET /api/logs/qa`
- `GET /api/logs/evidence`

## Konfiguration

Miljøvariabler:

```text
OLLAMA_HOST=http://127.0.0.1:11434
RAG_EMBED_MODEL=embeddinggemma
RAG_CHAT_MODEL=qwen3:1.7b
RAG_CHUNK_SIZE=100
RAG_CHUNK_OVERLAP=20
RAG_MAX_UPLOAD_MB=20
RAG_MAX_TOP_K=8
RAG_EMBED_BATCH=32
RAG_HOST=127.0.0.1
RAG_PORT=8000
```

Hvis embeddingmodellen ændres, markerer appen indekset som stale. Genbyg indekset fra webinterfacet.

## Test

Installer testafhængigheder:

```bash
pip install -r requirements-dev.txt
pytest
```

Projektet indeholder tests for chunking, cosine similarity, filnavne, TXT/DOCX-udtræk, upload, indeksbygning, spørgsmål/svar, evidence-log, Q&A-log, download, rydning og sletning.

Der findes også `tests/fake_server.py`, som kun er til en localhost-smoketest uden Ollama.

## Sikkerhed / drift

Denne udgave er lavet til **lokal enkeltbruger-drift**. Den binder til `127.0.0.1`, og `TrustedHostMiddleware` accepterer kun localhost/test-hosts. Der er derfor ikke login i brugerfladen.

Hvis du vil eksponere den på LAN eller Internet, bør du ikke blot ændre host til `0.0.0.0`. Tilføj først autentifikation, TLS via reverse proxy, adgangskontrol, rate limiting, passende backup og en bevidst politik for hvilke dokumenter der må uploades.

Dokumentudtræk er tekstbaseret. Scannede PDF'er uden tekstlag kræver OCR, hvilket denne version bevidst ikke udfører.

## Designvalg i forhold til den oprindelige demo

Den oprindelige demo bygger et RAM-indeks ved hver start. Webversionen gemmer chunks og embeddings i SQLite. Selve RAG-princippet er det samme:

```text
dokumenter → chunks → embeddings → similarity retrieval → top-k evidence → chatmodel → svar
```

Webversionen kalder Ollamas lokale HTTP API direkte (`/api/embed`, `/api/chat`, `/api/tags`) via `httpx`. Det reducerer en afhængighed, men ændrer ikke modellen eller RAG-flowet.
