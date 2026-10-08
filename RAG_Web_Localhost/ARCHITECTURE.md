# Arkitektur og designvalg

## RAG-flow

Webversionen beholder samme grundidé som den oprindelige undervisningsdemo:

```text
Dokument
  ↓
extract_text()
  ↓
chunk_text(size=100, overlap=20)
  ↓
Ollama /api/embed (embeddinggemma)
  ↓
SQLite: chunk + embedding

Spørgsmål
  ↓
Ollama /api/embed
  ↓
cosine similarity mod alle chunks
  ↓
top-k evidence
  ↓
Ollama /api/chat (qwen3:1.7b)
  ↓
svar + kildeetiketter
```

## Hvorfor SQLite?

Den oprindelige demo bygger alle embeddings igen ved hver programstart. Webversionen gemmer dem i `state/rag.sqlite3`. Appen gemmer SHA-256, filstørrelse og modification-time for de dokumenter, der blev indekseret. Hvis dokumentmappen eller embeddingmodellen ændres, markeres indekset som stale, og spørgsmål afvises, indtil indekset er genbygget. Det forhindrer at et svar laves fra et gammelt indeks uden at brugeren opdager det.

## Upload

Upload accepterer kun de filtyper, appen ved hvordan den kan udtrække tekst fra. Hele upload-batchen valideres, før filer flyttes på plads. Det betyder, at en ugyldig fil ikke bør efterlade halvdelen af en flerfil-upload som et skjult delresultat.

Efter upload forsøger appen automatisk at genbygge indekset. Hvis Ollama er nede, beholdes filerne, men interfacet viser at indekset ikke er klart. Brugeren kan genbygge senere.

## Sletning

Når et dokument slettes, fjernes selve filen og de tilhørende chunks i SQLite. Hvis der ikke er dokumenter tilbage, bliver indekset ikke-ready.

## Historik

For hvert succesfuldt spørgsmål skrives to separate append-only tekstlogs:

- `logs/qa_history.txt`: timestamp, spørgsmål, svar og kildeliste.
- `logs/evidence_history.txt`: timestamp, spørgsmål og den fulde retrieved evidence med similarity-score.

Webinterfacet viser indholdet som ren tekst med `textContent`; log- og dokumenttekst fortolkes ikke som HTML.

## Localhost-sikkerhed

`run.py` binder til `127.0.0.1` som standard. FastAPI bruger desuden TrustedHostMiddleware for localhost. Det gør løsningen egnet til lokal undervisning uden at lægge webappen direkte på LAN/Internet.

Hvis den skal eksponeres uden for localhost, skal sikkerhedsmodellen ændres: autentifikation, TLS/reverse proxy, host/origin-politik, rate limiting og adgangskontrol til dokumenter bør indføres først.

## Docker og flere workers

Den lokale udgave anbefales med én Uvicorn-worker. SQLite kan håndtere samtidige læsninger og serialiserede writes, men indeksbygning og tekstlogning er designet som en enkelt lokal applikationsproces. Skal den skaleres til flere brugere/processer, bør jobkø, central database og auth introduceres.
