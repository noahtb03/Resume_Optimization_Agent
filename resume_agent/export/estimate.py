"""Pure-Python one-page estimation (no LibreOffice needed).

Vertical-height budget model; element heights match docx.py styling. Bullet/text
height is approximate (depends on word-wrap, estimated via chars-per-line).
fill_target<1.0 biases toward trimming (never spill) while still filling the page.
"""
from __future__ import annotations

import math

from ..models.output import TailoredResume

PT_PER_IN = 72.0
USABLE_HEIGHT_PT = (11.0 - 2 * 0.7) * PT_PER_IN
TEXT_WIDTH_PT = (8.5 - 2 * 0.7) * PT_PER_IN


def _chars_per_line(font_pt: float, indent_in: float = 0.0) -> int:
    width = TEXT_WIDTH_PT - indent_in * PT_PER_IN
    # Arial average glyph is ~0.45 * font size in practice (calibrated against
    # LibreOffice rendering). Lower glyph width => more chars per line => fewer
    # estimated wrapped lines, matching real output.
    glyph = font_pt * 0.45
    return max(10, int(width / glyph))


def _wrapped_lines(text: str, font_pt: float, indent_in: float = 0.0) -> int:
    cpl = _chars_per_line(font_pt, indent_in)
    return max(1, math.ceil(len(text) / cpl))


def _line_pt(font_pt: float) -> float:
    return font_pt * 1.20


def _short_link(url: str) -> str:
    u = url.lower()
    if "github.com" in u:
        return "GitHub"
    if "linkedin.com" in u:
        return "LinkedIn"
    if "noahbennettdev" in u or "portfolio" in u:
        return "Portfolio"
    return url.split("://")[-1].lstrip("www.").rstrip("/")


def estimate_height_pt(resume: TailoredResume) -> float:
    h = 0.0
    c = resume.contact

    h += _line_pt(16) + 2
    bits = [b for b in (c.phone, c.email, c.location) if b]
    bits += [_short_link(l) for l in c.links]
    if bits:
        h += _wrapped_lines("  |  ".join(bits), 8.5) * _line_pt(8.5) + 4

    def heading() -> float:
        return _line_pt(10.5) + 7 + 2 + 3

    def bullet(text: str) -> float:
        return _wrapped_lines(text, 9, indent_in=0.5) * _line_pt(9) + 2

    def entry_header(has_location: bool) -> float:
        v = _line_pt(9.5) + 4 + 1
        if has_location:
            v += _line_pt(8.5) + 1
        return v

    for sec in resume.section_order:
        if sec == "summary" and resume.summary and resume.summary.text.strip():
            h += heading()
            h += _wrapped_lines(resume.summary.text, 9) * _line_pt(9) + 2
        elif sec == "skills" and resume.skills:
            h += heading()
            by_cat: dict[str, list[str]] = {}
            for sk in resume.skills:
                by_cat.setdefault(sk.category or "Other", []).append(sk.name)
            for cat, names in by_cat.items():
                line = f"{cat}: {', '.join(names)}"
                h += _wrapped_lines(line, 9) * _line_pt(9) + 1
        elif sec == "experience" and resume.experiences:
            h += heading()
            for exp in resume.experiences:
                h += entry_header(bool(exp.location))
                for b in exp.bullets:
                    h += bullet(b.text)
        elif sec == "projects" and resume.projects:
            h += heading()
            for pr in resume.projects:
                h += entry_header(False)
                for b in pr.bullets:
                    h += bullet(b.text)
        elif sec == "education" and resume.education:
            h += heading()
            for ed in resume.education:
                h += entry_header(bool(ed.institution))
                if ed.details:
                    h += _wrapped_lines("  |  ".join(ed.details), 8.5) * _line_pt(8.5) + 2
        elif sec == "certifications" and resume.certifications:
            h += heading()
            for _ in resume.certifications:
                h += _line_pt(9) + 2
    return h


def estimate_pages(resume: TailoredResume, fill_target: float = 0.96) -> int:
    # Compare against usable height with a small tolerance so a page that is
    # merely full (not overflowing) counts as one page rather than rounding up.
    # The estimator is approximate; without tolerance it over-trims at the boundary.
    total = estimate_height_pt(resume)
    if total <= USABLE_HEIGHT_PT * 1.04:   # within ~4% of a full page -> one page
        return 1
    budget = USABLE_HEIGHT_PT * fill_target
    return max(1, math.ceil(total / budget))