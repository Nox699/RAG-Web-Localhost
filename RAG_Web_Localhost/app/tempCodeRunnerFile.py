essage = store.provider.health()
        return {"index": index, "ollama": {"ok": ollama_ok, "message": ollama_message}}

    @app.get("/api/documents")
    def documents():
        return {"documents": store.list_documents()}

    @app.post("/api/documents")
    async def upload_documents(files: list[UploadFile] = File(...)):
        if not files:
            raise HTTPException(400, "No files supplied")
        try:
            items = []
            for upload in files:
                content = await upload.read(settings.max_upload_bytes + 1)
                items.append((upload.filename or "", content))
            saved = store.save_uploads(items)
        except DocumentError as exc: