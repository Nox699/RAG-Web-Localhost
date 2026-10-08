const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
let activeLog = "qa";
let chosenFiles = [];

function escapeNothing(value) { return value ?? ""; }
function showToast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.remove("hidden");
  window.setTimeout(() => el.classList.add("hidden"), 3200);
}
function showMessage(selector, message, type="success") {
  const el = $(selector);
  el.textContent = message;
  el.className = `message ${type}`;
}
function hideMessage(selector) { $(selector).classList.add("hidden"); }
function bytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024*1024) return `${(n/1024).toFixed(1)} KB`;
  return `${(n/1024/1024).toFixed(1)} MB`;
}
async function api(url, options={}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { const body = await response.json(); detail = body.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

async function refreshStatus() {
  try {
    const data = await api("/api/status");
    const status = $("#statusBadge");
    if (data.index.ready && data.ollama.ok) {
      status.textContent = "Klar";
      status.className = "status ok";
    } else {
      status.textContent = data.ollama.ok ? "Indeks kræver handling" : "Ollama ikke klar";
      status.className = "status bad";
    }
    $("#statDocs").textContent = data.index.documents;
    $("#statChunks").textContent = data.index.chunks;
    $("#statEmbed").textContent = data.index.embed_model;
    $("#statChat").textContent = data.index.chat_model;
    $("#indexReason").textContent = `Status: ${data.index.reason}${data.index.built_at ? ` · bygget ${data.index.built_at}` : ""}`;
    $("#indexBadge").textContent = data.index.ready ? "Klar" : "Ikke klar";
    $("#ollamaState").textContent = data.ollama.ok ? "✓ Klar" : "✕ Ikke klar";
    $("#ollamaMessage").textContent = data.ollama.message;
    $("#ollamaModels").textContent = `${data.index.embed_model} · ${data.index.chat_model}`;
    return data;
  } catch (err) {
    $("#statusBadge").textContent = "Serverfejl";
    $("#statusBadge").className = "status bad";
    throw err;
  }
}

async function refreshDocuments() {
  const data = await api("/api/documents");
  const list = $("#documentsList");
  list.replaceChildren();
  if (!data.documents.length) {
    const empty = document.createElement("div");
    empty.className = "placeholder";
    empty.textContent = "Ingen dokumenter endnu.";
    list.appendChild(empty);
    return;
  }
  for (const doc of data.documents) {
    const row = document.createElement("div");
    row.className = "document-row";
    const main = document.createElement("div");
    const name = document.createElement("div");
    name.className = "document-name";
    name.textContent = doc.name;
    const meta = document.createElement("div");
    meta.className = "document-meta";
    meta.textContent = `${bytes(doc.size_bytes)} · ${doc.chunks} chunks`;
    main.append(name, meta);
    const state = document.createElement("div");
    state.className = `doc-status ${doc.indexed ? "ok" : "pending"}`;
    state.textContent = doc.indexed ? "Indekseret" : "Afventer indeks";
    const modified = document.createElement("div");
    modified.className = "document-meta";
    modified.textContent = new Date(doc.modified).toLocaleString("da-DK");
    const del = document.createElement("button");
    del.className = "delete-doc";
    del.textContent = "Fjern";
    del.addEventListener("click", async () => {
      if (!confirm(`Fjern ${doc.name}?`)) return;
      del.disabled = true;
      try {
        await api(`/api/documents/${encodeURIComponent(doc.name)}`, {method:"DELETE"});
        await Promise.all([refreshDocuments(), refreshStatus()]);
        showToast(`${doc.name} blev fjernet`);
      } catch (err) { showToast(err.message); }
      finally { del.disabled = false; }
    });
    row.append(main, state, modified, del);
    list.appendChild(row);
  }
}

async function ask() {
  hideMessage("#chatError");
  const question = $("#question").value.trim();
  if (!question) return showMessage("#chatError", "Skriv et spørgsmål først.", "error");
  const btn = $("#askBtn");
  btn.disabled = true;
  btn.textContent = "Arbejder…";
  $("#answer").textContent = "Henter evidence og genererer svar…";
  $("#answer").classList.add("placeholder");
  $("#evidence").replaceChildren();
  try {
    const data = await api("/api/ask", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({question, top_k: Number($("#topK").value)})
    });
    $("#answer").textContent = data.answer;
    $("#answer").classList.remove("placeholder");
    $("#answerMeta").textContent = `${data.evidence.length} chunks`;
    for (const hit of data.evidence) {
      const item = document.createElement("article");
      item.className = "evidence-item";
      const head = document.createElement("div");
      head.className = "evidence-head";
      const source = document.createElement("span");
      source.className = "evidence-source";
      source.textContent = hit.source;
      const score = document.createElement("span");
      score.textContent = `similarity ${hit.similarity.toFixed(3)}`;
      const text = document.createElement("div");
      text.className = "evidence-text";
      text.textContent = hit.text;
      head.append(source, score);
      item.append(head, text);
      $("#evidence").appendChild(item);
    }
  } catch (err) {
    $("#answer").textContent = "Svaret kunne ikke genereres.";
    showMessage("#chatError", err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Spørg";
  }
}

async function upload() {
  hideMessage("#uploadMessage");
  if (!chosenFiles.length) return showMessage("#uploadMessage", "Vælg mindst én fil.", "warn");
  const btn = $("#uploadBtn");
  btn.disabled = true;
  btn.textContent = "Uploader…";
  const form = new FormData();
  chosenFiles.forEach(file => form.append("files", file));
  try {
    const result = await api("/api/documents", {method:"POST", body:form});
    chosenFiles = [];
    $("#fileInput").value = "";
    $("#dropZone span").textContent = "eller klik for at vælge";
    if (result.warning) showMessage("#uploadMessage", `Filer gemt, men indeks kunne ikke genbygges: ${result.warning}`, "warn");
    else showMessage("#uploadMessage", `${result.saved.length} fil(er) uploadet og indekseret.`, "success");
    await Promise.all([refreshDocuments(), refreshStatus()]);
  } catch (err) {
    showMessage("#uploadMessage", err.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Upload & indeksér";
  }
}

async function rebuild() {
  const btn = $("#rebuildBtn");
  btn.disabled = true;
  btn.textContent = "Genbygger…";
  hideMessage("#uploadMessage");
  try {
    await api("/api/index/rebuild", {method:"POST"});
    showMessage("#uploadMessage", "Indekset er genbygget.", "success");
    await Promise.all([refreshDocuments(), refreshStatus()]);
  } catch (err) { showMessage("#uploadMessage", err.message, "error"); }
  finally { btn.disabled = false; btn.textContent = "Genbyg hele indeks"; }
}

async function loadLog() {
  const text = await api(`/api/logs/${activeLog}`);
  $("#logContent").textContent = text || "Loggen er tom.";
  $("#logTitle").textContent = activeLog === "qa" ? "Spørgsmål & svar" : "Spørgsmål & evidence";
  $("#downloadLog").href = `/api/logs/${activeLog}/download`;
}

$$('.tab').forEach(btn => btn.addEventListener('click', async () => {
  $$('.tab').forEach(x => x.classList.toggle('active', x === btn));
  $$('.tab-panel').forEach(x => x.classList.remove('active'));
  $(`#tab-${btn.dataset.tab}`).classList.add('active');
  if (btn.dataset.tab === 'documents') await refreshDocuments();
  if (btn.dataset.tab === 'logs') await loadLog();
  if (btn.dataset.tab === 'system') await refreshStatus();
}));
$$('.log-tab').forEach(btn => btn.addEventListener('click', async () => {
  activeLog = btn.dataset.log;
  $$('.log-tab').forEach(x => x.classList.toggle('active', x === btn));
  await loadLog();
}));
$("#askBtn").addEventListener("click", ask);
$("#question").addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") ask(); });
$("#fileInput").addEventListener("change", e => {
  chosenFiles = [...e.target.files];
  $("#dropZone span").textContent = chosenFiles.length ? chosenFiles.map(f => f.name).join(", ") : "eller klik for at vælge";
});
for (const event of ["dragenter", "dragover"]) $("#dropZone").addEventListener(event, e => { e.preventDefault(); $("#dropZone").classList.add("drag"); });
for (const event of ["dragleave", "drop"]) $("#dropZone").addEventListener(event, e => { e.preventDefault(); $("#dropZone").classList.remove("drag"); });
$("#dropZone").addEventListener("drop", e => {
  chosenFiles = [...e.dataTransfer.files];
  $("#dropZone span").textContent = chosenFiles.length ? chosenFiles.map(f => f.name).join(", ") : "eller klik for at vælge";
});
$("#uploadBtn").addEventListener("click", upload);
$("#rebuildBtn").addEventListener("click", rebuild);
$("#refreshDocsBtn").addEventListener("click", refreshDocuments);
$("#clearLogBtn").addEventListener("click", async () => {
  if (!confirm("Ryd denne logfil?")) return;
  await api(`/api/logs/${activeLog}`, {method:"DELETE"});
  await loadLog();
  showToast("Loggen blev ryddet");
});

Promise.all([refreshStatus(), refreshDocuments()]).catch(err => showToast(err.message));
