"""argparse CLI over the services. Subcommands: parse, lint, generate.

BYOK: the key is read here (CLI layer) from --api-key, a .env file, or the
ANTHROPIC_API_KEY env var. Core/service code never touches env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .enrich_service import enrich_profile
from .llm.client import AnthropicClient
from .service import generate_resume
from .core.lint_source import lint_source, format_findings
from .parsing.parser import parse_resumes
from .export.docx import render_docx
from .export.fit import fit_to_one_page


def _load_dotenv() -> None:
    """Load .env into the environment at the CLI layer only (core never reads env)."""
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(override=False)
        return
    except Exception:
        pass
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        pass


def _require_key(args) -> str | None:
    key = getattr(args, "api_key", None) or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("error: provide --api-key or set ANTHROPIC_API_KEY (in .env or env)",
              file=sys.stderr)
    return key


class _StubClient:
    """Offline client for --dry-run on `generate` only."""

    def complete(self, *, system: str, user: str, max_tokens: int = 1500) -> str:
        if "information extractor" in system.lower():
            return json.dumps({
                "title": None, "seniority": "unknown", "required_skills": [],
                "preferred_skills": [], "ats_keywords": [], "responsibilities": [],
                "hard_requirements": [],
            })
        in_records, bullets = False, []
        for line in user.splitlines():
            if line.startswith("SELECTED RECORDS"):
                in_records = True
                continue
            if in_records and line.strip().startswith(("LIMITS", "Produce")):
                break
            if in_records and 'text="' in line:
                bid = line.strip().split()[0]
                text = line.split('text="', 1)[1].split('"', 1)[0]
                bullets.append({"text": text, "source_bullet_ids": [bid],
                                "used_skill_ids": [], "used_metric_ids": [],
                                "used_inference_ids": []})
        return json.dumps({"summary": None, "bullets": bullets})


def _cmd_parse(args) -> int:
    key = _require_key(args)
    if not key:
        return 2
    client = AnthropicClient(api_key=key, model=args.model)
    draft = parse_resumes(args.inputs, client)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(draft.source, f, indent=2)
    review_path = args.out.rsplit(".", 1)[0] + ".review.txt"
    with open(review_path, "w", encoding="utf-8") as f:
        f.write("REVIEW THESE BEFORE TRUSTING THE DRAFT\n")
        f.write("=" * 40 + "\n\n")
        if draft.notes:
            f.write("Extraction notes:\n")
            for n in draft.notes:
                f.write(f"  - {n}\n")
            f.write("\n")
        if not draft.flags:
            f.write("No contradictions or unverified numbers flagged.\n")
        for fl in draft.flags:
            f.write(f"[{fl.kind}] {fl.where}\n  {fl.message}\n")
            for opt in fl.options:
                f.write(f"    - option: {opt}\n")
            f.write("\n")
    print(f"wrote draft source -> {args.out}")
    print(f"wrote review file  -> {review_path}  ({len(draft.flags)} flag(s))")
    print("NEXT: read the review file, fix the draft, then run `resume-agent lint`.")
    return 0


def _cmd_lint(args) -> int:
    with open(args.source, encoding="utf-8") as f:
        raw = json.load(f)
    enriched = enrich_profile(raw)
    findings = lint_source(enriched)
    print(format_findings(findings))
    return 1 if any(x.level == "error" for x in findings) else 0


def _cmd_generate(args) -> int:
    with open(args.source, encoding="utf-8") as f:
        raw_source = json.load(f)
    with open(args.jd, encoding="utf-8") as f:
        jd_text = f.read()
    enriched = enrich_profile(raw_source)

    if args.dry_run:
        client = _StubClient()
    else:
        key = _require_key(args)
        if not key:
            return 2
        client = AnthropicClient(api_key=key, model=args.model)

    result = generate_resume(enriched, jd_text, client)
    text = json.dumps(result.model_dump(mode="json"), indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out} (llm_calls_used={result.meta.llm_calls_used})")
    else:
        print(text)
    return 0


def _cmd_export(args) -> int:
    from .models.output import TailoredResume
    with open(args.input, encoding="utf-8") as f:
        resume = TailoredResume.model_validate(json.load(f))
    if args.one_page:
        result = fit_to_one_page(resume, args.out)
        print(f"wrote {args.out}")
        print(result.note)
    else:
        render_docx(resume, args.out)
        print(f"wrote {args.out}")
    return 0

def _cmd_serve(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("error: web UI needs extra packages. Run: pip install -e \".[web]\"",
              file=sys.stderr)
        return 2
    print(f"Resume Agent UI -> http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    uvicorn.run("resume_agent.web:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="resume-agent")
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--api-key", default=None, help="Anthropic API key (BYOK)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("parse", help="parse 1-3 resumes into a draft source bank")
    sp.add_argument("inputs", nargs="+", help="resume files (.pdf/.txt/.md)")
    sp.add_argument("--out", default="source_draft.json")
    sp.set_defaults(func=_cmd_parse)

    sl = sub.add_parser("lint", help="check a source file for data-contract issues")
    sl.add_argument("--source", required=True)
    sl.set_defaults(func=_cmd_lint)

    sg = sub.add_parser("generate", help="generate a tailored resume from source + JD")
    sg.add_argument("--source", required=True)
    sg.add_argument("--jd", required=True)
    sg.add_argument("--out", default=None)
    sg.add_argument("--dry-run", action="store_true")
    sg.set_defaults(func=_cmd_generate)

    se = sub.add_parser("export", help="render a tailored resume JSON to a .docx file")
    se.add_argument("--input", required=True, help="tailored resume JSON (from generate)")
    se.add_argument("--out", default="resume.docx")
    se.add_argument("--one-page", action="store_true",
                    help="trim lowest-ranked bullets until it fits one page (needs LibreOffice)")
    se.set_defaults(func=_cmd_export)

    sv = sub.add_parser("serve", help="launch the local web UI in your browser")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--reload", action="store_true")
    sv.set_defaults(func=_cmd_serve)

    args = p.parse_args(argv)
    _load_dotenv()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
