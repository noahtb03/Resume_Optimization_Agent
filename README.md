# Resume Optimization Agent

Tailor your real experience to a job posting — **without the AI inventing anything.**

This is not a "let an AI write my résumé" tool. It uses Claude for one narrow job:
rephrasing accomplishments *you already wrote* to better match a job posting.
Everything else — what's true, what gets included, the structure, the final
document — is controlled by deterministic code. The model can reword and reorder
your real experience; it is fenced so it **cannot add a skill, number, employer,
or claim you didn't provide.**

---

## Quick start (the easy way — web app)

If you just want to use it, this is all you need.

**1. Get the project onto your computer.** Either:
- Download it: on the GitHub page, click the green **Code** button → **Download ZIP**, then unzip it. Or
- Clone it (if you have git): `git clone https://github.com/noahtb03/Resume_Optimization_Agent.git`

**2. Open the folder in your IDE** (VS Code, etc.) and open a terminal in it
(`Terminal → New Terminal`).

**3. Install it** (one-time). You need **Python 3.11+** ([get it here](https://www.python.org/downloads/) if `python --version` shows older or nothing):

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[web]"
```

Mac / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[web]"
```
> Windows: if activation is blocked, run once `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (answer `Y`), then try again.

**4. Add your Anthropic API key** (one-time). Copy the file `.env.example` to a new
file named `.env`, open it, and paste your key after the `=`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```
Get a key at [console.anthropic.com](https://console.anthropic.com) — new accounts
include free credit, and each résumé costs about 1–2 cents. Your key stays on your
machine and is never uploaded (`.env` is gitignored).

**5. Start the app:**
```powershell
resume-agent serve
```

**6. Open the link** it prints — **http://127.0.0.1:8000** — in your browser.

That's it. In the browser you:
1. Upload 1–3 of your existing résumés (PDF) — it builds your experience bank and
   flags anything that needs your decision.
2. Paste a job description.
3. Get a tailored preview, then **Download .docx** — a clean, one-page,
   ATS-friendly résumé.

> Tip: close `resume.docx` in Word before re-downloading, or Windows won't let it
> overwrite the file.

---

## How it works

```
  upload résumés ─► review flags ─► paste job ─► generate ─► download .docx
```

The core idea: **the AI rephrases, your data controls the facts.** When the model
writes a tailored bullet, it must declare which of your original bullets, skills,
and numbers it used. Deterministic code then verifies every one of those against
your source. If the model tries to use something you didn't provide, the check
fails — it gets one chance to fix it, and otherwise falls back to your original
wording. That's why it can't fabricate.

It also:
- Keeps each accomplishment as its **own bullet** (never fuses two into one).
- Preserves your **numbers exactly** (95% stays 95%) by treating them as
  structured facts.
- Surfaces your **strongest, most relevant** experience per job, and groups your
  skills under headings that fit the posting (e.g. a "Full Stack" line for a
  full-stack role) — using only skills you actually have.
- Fits everything to **one page**.

---

## Other ways to use it

### Command line

Everything the web app does is also available as commands, if you prefer the terminal:

```powershell
# build an experience bank from your résumés (writes my_resume.json + a review file)
resume-agent parse Resume1.pdf Resume2.pdf --out my_resume.json

# check your data for problems before spending anything (free)
resume-agent lint --source my_resume.json

# tailor to a job (job.txt is the posting saved as plain text)
resume-agent generate --source my_resume.json --jd job.txt --out tailored.json

# render to a one-page Word doc
resume-agent export --input tailored.json --out resume.docx --one-page
```

Add `--dry-run` to `generate` to test the whole pipeline offline with a stand-in
model (no API key, no cost).

### Maintain your experience bank by hand

The parser writes a `my_resume.json` file — your master list of experience, bigger
than fits on any one résumé. You can edit it directly to fix wording, correct a
skill's category, adjust which accomplishments are strongest, or add detail. The
tool picks the best parts for each job from whatever's in this file, so a richer,
accurate bank produces better résumés.

---

## Making it work better

- **One bank, many jobs.** Build `my_resume.json` once; for each new posting, just
  paste a new job description (web) or point `--jd` at a new file (CLI). The tool
  re-picks the best content each time.
- **Review the flags.** When you upload multiple résumés that disagree on a fact,
  it flags the contradiction and asks you to pick the accurate version. *You* decide
  what's true — the tool never guesses on facts about your career.
- **Read what it produces.** It guarantees it won't *add* anything you didn't
  provide, but it can't know whether your source itself is accurate. Always read the
  generated résumé before sending it — you're the final check.
- **Coverage report.** The result shows which job keywords your experience covers
  and which it's missing — useful for deciding whether to apply or what real
  experience to highlight. It will **not** add a missing skill (e.g. "AWS") you
  don't have; it lists it as a gap instead.
- **Exact one-page fitting (optional).** Without extra software, page length is
  estimated. For pixel-exact fitting, install
  [LibreOffice](https://www.libreoffice.org/) — the tool detects it automatically.
- **Tune the ranking (advanced).** Each bullet in `my_resume.json` has a
  `strength` score (1–10) that boosts your best work; skill categories control
  grouping. Both are plain fields you can edit.

---

## Cost & privacy

- **Cost:** your own Anthropic API credits. ~1–2 cents per résumé; parsing costs a
  bit more. `lint`, `--dry-run`, and `export` are free. You can set a spending cap
  in the Anthropic console.
- **Privacy:** your API key and résumé data stay on your machine. When you generate
  or parse, your résumé content and the job description are sent to Anthropic's API
  (that's how tailoring works), subject to Anthropic's policies — nothing is sent
  anywhere else, and nothing is stored.

---

## Limitations (read these)

This tool is honest about what it can and can't guarantee:

- **It verifies attribution, not perfect phrasing.** It guarantees every skill,
  number, employer, and date comes from your data, and that numbers are reproduced
  exactly. It does **not** guarantee a rephrased bullet is a flawless paraphrase —
  so **read your generated résumé before sending it.** You are the final check.
- **It's only as accurate as your source.** If one of your uploaded résumés
  overstates something, the tool will faithfully carry that forward. Garbage in,
  garbage out — confirm the flagged items and keep your experience bank truthful.
- **You must resolve contradictions.** When uploaded résumés disagree, it asks
  *you* which version is true. It never decides facts about your career on its own.
- **"One page" without LibreOffice is an estimate.** Close, but for a guarantee,
  install LibreOffice or just check the length yourself.
- **English-first.** Built and tested for English résumés. Other Latin-script
  languages may work with reduced quality; non-Latin scripts are experimental.
- **Not a cover-letter or career-advice tool.** It tailors résumé content from your
  real experience. That's the whole job.

---

*Built as a constrained-LLM system: structured experience records, deterministic
relevance scoring, provenance validation, and bounded repair/fallback to generate
job-specific résumés without unsupported claims.*
