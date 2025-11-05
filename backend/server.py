from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .statement_analyzer import analyze_pdf_bytes

logger = logging.getLogger(__name__)

app = FastAPI(title="Statement Analyzer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", tags=["analysis"])
async def analyze(
    file: UploadFile = File(...),
    password: str | None = Form(default=None),
) -> JSONResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="El archivo está vacío")

        result = analyze_pdf_bytes(
            pdf_bytes,
            statement_label=Path(file.filename).stem,
            password=password,
        )
        return JSONResponse(result.to_dict())
    except HTTPException:
        logger.warning("Error HTTP")
        raise
    except ValueError as exc:
        logger.warning("Contraseña incorrecta para PDF protegido")
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error al procesar el PDF", exc_info=exc)
        raise HTTPException(status_code=500, detail="No se pudo procesar el PDF") from exc
