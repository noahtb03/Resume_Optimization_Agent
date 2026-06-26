"""One-page fitting.

The honest version of 'one page': render the DOCX, measure how many pages it
actually produces, and if it overflows, trim the lowest-priority content and
re-render until it fits (or we run out of safe trims).

Page measurement needs a renderer (LibreOffice). If LibreOffice is not
installed, we fall back to a heuristic line-count estimate and warn that exact
one-page fit can't be guaranteed without it. This keeps the feature honest:
we never *claim* one page we couldn't verify.

Trim order (least-costly first): drop the last (lowest-ranked) bullet of the
longest experience/project, since the selector already ranked bullets by
relevance, so the last ones are the least important.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..models.output import TailoredResume
from .docx import render_docx
from .estimate import estimate_pages


class FitResult:
    def __init__(self, resume: TailoredResume, pages: int | None, trims: int, note: str):
        self.resume = resume
        self.pages = pages            # measured/estimated page count
        self.trims = trims
        self.note = note


def _pages(resume: TailoredResume, docx_path: str) -> tuple[int | None, str]:
    """Return (page_count, method). Tries exact LibreOffice render first; falls
    back to the pure-Python estimator. method is 'measured' or 'estimated'."""
    exact = _measure_pages(docx_path)
    if exact is not None:
        return exact, "measured"
    return estimate_pages(resume), "estimated"


def _measure_pages(docx_path: str) -> int | None:
    """Return page count by converting to PDF with LibreOffice, or None if it
    isn't available."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    with tempfile.TemporaryDirectory() as td:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", td, docx_path],
                capture_output=True, timeout=120, check=True,
            )
            pdfs = list(Path(td).glob("*.pdf"))
            if not pdfs:
                return None
            return _pdf_page_count(str(pdfs[0]))
        except Exception:
            return None


def _pdf_page_count(pdf_path: str) -> int | None:
    try:
        from pypdf import PdfReader
        return len(PdfReader(pdf_path).pages)
    except Exception:
        return None


def _trim_one(resume: TailoredResume, min_exp_bullets: int = 3, min_proj_bullets: int = 2) -> bool:
    """Remove a single lowest-priority bullet in place, respecting per-section
    floors. Returns True if it trimmed. Only items still ABOVE their floor are
    eligible; among those, the one with the most bullets is trimmed first
    (dropping its last, selector-ranked-lowest bullet). When everything is at its
    floor, returns False so the fitter stops rather than gutting the resume."""
    candidates = []
    for e in resume.experiences:
        if len(e.bullets) > min_exp_bullets:
            candidates.append(e)
    for p in resume.projects:
        if len(p.bullets) > min_proj_bullets:
            candidates.append(p)
    if not candidates:
        return False
    candidates.sort(key=lambda it: len(it.bullets), reverse=True)
    candidates[0].bullets.pop()  # drop last (lowest-ranked) bullet
    return True


def fit_to_one_page(resume: TailoredResume, out_path: str, max_trims: int = 12) -> FitResult:
    """Render, measure (or estimate), and trim until it fits one page or we
    can't trim more."""
    render_docx(resume, out_path)
    pages, method = _pages(resume, out_path)

    trims = 0
    while pages and pages > 1 and trims < max_trims:
        if not _trim_one(resume):
            break
        render_docx(resume, out_path)
        pages, method = _pages(resume, out_path)
        trims += 1

    qualifier = "" if method == "measured" else " (estimated; install LibreOffice for exact verification)"
    if pages == 1:
        base = f"Fits on one page{qualifier}"
        note = f"{base} after {trims} trim(s)." if trims else f"{base}."
    else:
        note = (f"Still ~{pages} pages after {trims} trim(s){qualifier}; could not reduce "
                f"further without dropping whole sections. Consider shortening source bullets.")
    return FitResult(resume, pages, trims, note)
