"""Deterministic text extraction from resume files (PDF or plain text).

No LLM and no network here -- this only turns files into raw text. The LLM
structuring step (parser.py) consumes this text. Extraction is best-effort and
intentionally surfaces what it pulled so the human-review gate can catch
garbled multi-column output.
"""
from __future__ import annotations

import pathlib


class ExtractionResult:
    def __init__(self, path: str, text: str, warnings: list[str]):
        self.path = path
        self.text = text
        self.warnings = warnings


def extract_text(path: str) -> ExtractionResult:
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    suffix = p.suffix.lower()
    warnings: list[str] = []

    if suffix in (".txt", ".md"):
        return ExtractionResult(path, p.read_text(encoding="utf-8", errors="replace"), warnings)

    if suffix == ".pdf":
        text = _extract_pdf(p, warnings)
        if len(text.strip()) < 50:
            warnings.append(
                f"{p.name}: very little text extracted (~{len(text.strip())} chars) -- "
                "the PDF may be scanned or image-based; review the draft carefully."
            )
        return ExtractionResult(path, text, warnings)

    raise ValueError(f"unsupported file type: {suffix} (use .pdf, .txt, or .md)")


def _extract_pdf(p: pathlib.Path, warnings: list[str]) -> str:
    # Prefer pdftotext -layout (best for multi-column resumes); fall back to pypdf.
    import shutil
    import subprocess

    if shutil.which("pdftotext"):
        try:
            out = subprocess.run(
                ["pdftotext", "-layout", str(p), "-"],
                capture_output=True, text=True, timeout=60,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout
        except Exception as e:
            warnings.append(f"{p.name}: pdftotext failed ({e}); trying pypdf.")

    try:
        from pypdf import PdfReader
        reader = PdfReader(str(p))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        warnings.append(f"{p.name}: pypdf extraction failed ({e}).")
        return ""
