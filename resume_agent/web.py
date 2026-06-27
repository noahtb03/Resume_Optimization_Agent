"""Local web backend for the Resume Optimization Agent.

Thin HTTP layer over the existing services -- no new resume logic. BYOK: the key
is read from the ANTHROPIC_API_KEY environment (loaded from .env at startup) or
optionally passed per request; it is never persisted. Designed to run LOCALLY
(localhost), so the page and the API share one machine.

Run with:  uvicorn resume_agent.web:app --reload
or:        resume-agent serve
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .enrich_service import enrich_profile
from .core.validate_source import load_source, SourceValidationError
from .core.lint_source import lint_source, format_findings
from .service import generate_resume
from .llm.client import AnthropicClient
from .parsing.parser import parse_resumes
from .export.fit import fit_to_one_page
from .export.docx import render_docx
from .models.output import TailoredResume

app = FastAPI(title="Resume Optimization Agent")

_STATIC = Path(__file__).parent / "web_static"


def _key(form_key: str | None) -> str:
    key = (form_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise HTTPException(400, "No API key. Set ANTHROPIC_API_KEY in .env or enter one.")
    return key


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/api/has-key")
def has_key() -> dict:
    """Lets the page hide the key field when .env already provides one."""
    return {"has_key": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@app.post("/api/parse")
async def api_parse(files: list[UploadFile] = File(...), api_key: str = Form(None)) -> JSONResponse:
    key = _key(api_key)
    if len(files) > 3:
        raise HTTPException(400, "Upload at most 3 resumes.")
    paths: list[str] = []
    tmpdir = tempfile.mkdtemp()
    try:
        for f in files:
            p = Path(tmpdir) / (f.filename or "resume.pdf")
            p.write_bytes(await f.read())
            paths.append(str(p))
        client = AnthropicClient(api_key=key, model=AnthropicClient.FAST_MODEL)
        draft = parse_resumes(paths, client)
        return JSONResponse({
            "source": draft.source,
            "flags": [fl.model_dump() for fl in draft.flags],
            "notes": draft.notes,
        })
    except Exception as e:
        raise HTTPException(500, f"Parse failed: {e}")


@app.post("/api/lint")
async def api_lint(source: str = Form(...)) -> JSONResponse:
    try:
        raw = json.loads(source)
        enriched = enrich_profile(raw)
        findings = lint_source(enriched)
    except SourceValidationError as e:
        raise HTTPException(400, f"Invalid source: {e}")
    except Exception as e:
        raise HTTPException(400, f"Lint error: {e}")
    return JSONResponse({
        "ok": not any(f.level == "error" for f in findings),
        "report": format_findings(findings),
        "findings": [{"level": f.level, "where": f.where, "message": f.message} for f in findings],
    })


@app.post("/api/generate")
async def api_generate(source: str = Form(...), jd: str = Form(...),
                       api_key: str = Form(None)) -> JSONResponse:
    key = _key(api_key)
    try:
        raw = json.loads(source)
        enriched = enrich_profile(raw)
    except Exception as e:
        raise HTTPException(400, f"Invalid source JSON: {e}")
    try:
        client = AnthropicClient(api_key=key)
        result = generate_resume(enriched, jd, client)
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {e}")
    return JSONResponse(result.model_dump(mode="json"))


@app.post("/api/export")
async def api_export(tailored: str = Form(...), one_page: bool = Form(True)) -> FileResponse:
    try:
        resume = TailoredResume.model_validate(json.loads(tailored))
    except Exception as e:
        raise HTTPException(400, f"Invalid tailored JSON: {e}")
    out = Path(tempfile.mkdtemp()) / "resume.docx"
    try:
        if one_page:
            fit_to_one_page(resume, str(out))
        else:
            render_docx(resume, str(out))
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")
    return FileResponse(
        str(out),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="resume.docx",
    )


# serve static assets if any are added later
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")