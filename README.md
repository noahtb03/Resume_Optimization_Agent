# Resume Optimization Agent

Turn your existing résumés plus a job description into a tailored, ATS-friendly,
one-page Word résumé — **without the AI inventing anything about you.**

This is not a "let an AI write my résumé" tool. It uses an AI model (Claude) for
one narrow job: rephrasing accomplishments *you already wrote* to match a job
posting's language. Everything else — what's true, what gets included, the
structure, the final document — is handled by deterministic code. The model is
never allowed to invent a skill, a number, a job, or a date you didn't provide.

---

## Table of contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [What you'll need](#what-youll-need)
- [Step 1 — Install it](#step-1--install-it)
- [Step 2 — Add your Anthropic API key](#step-2--add-your-anthropic-api-key)
- [Step 3 — Build your "experience bank"](#step-3--build-your-experience-bank)
- [Step 4 — Generate a tailored résumé](#step-4--generate-a-tailored-résumé)
- [Step 5 — Export to a Word document](#step-5--export-to-a-word-document)
- [Command reference](#command-reference)
- [Tips and tuning](#tips-and-tuning)
- [Cost](#cost)
- [Privacy](#privacy)
- [Limitations (read these)](#limitations-read-these)

---

## What it does

You give it:
1. Your résumé(s) — one or more, as PDFs (or a structured file you maintain).
2. A job description (a plain text file).
3. Your own Anthropic API key.

It gives you back a tailored, one-page `.docx` résumé that:
- Reorders and rephrases **your real accomplishments** to match the job.
- Includes only skills, numbers, employers, and dates that are in **your** data.
- Surfaces your strongest (quantified, technical) bullets even when they don't
  share many keywords with the posting.
- Fits on one page, with clean formatting that applicant-tracking systems (ATS)
  can read — single column, no tables or graphics, clickable contact links.

---

## How it works

The tool runs as a pipeline. Each step is a command you run:

```
  parse  ──►  (you review)  ──►  lint  ──►  generate  ──►  export
  PDFs        confirm facts       check       tailor        one-page
  → JSON      & numbers           the data    to the job    .docx
```

The key design idea: **the AI rephrases, your code controls the facts.** When
the model writes a tailored bullet, it must declare which of your original
bullets, skills, and metrics it used. Deterministic code then verifies every one
of those against your source data. If the model tries to use something you didn't
provide, the check fails, it gets one chance to fix it, and if it still fails the
tool falls back to your original wording. That's why it can't fabricate.

---

## What you'll need

- **A computer** (Windows, Mac, or Linux). This guide assumes you have **VS Code**
  and can open its built-in terminal (`Terminal → New Terminal`).
- **Python 3.11 or newer.** Check by running `python --version`. If it's older
  than 3.11 (or "command not found"), install the latest from
  [python.org](https://www.python.org/downloads/).
- **An Anthropic API key** (instructions below — it costs a few cents per résumé).
- *(Optional)* **LibreOffice**, only if you want pixel-exact one-page fitting.
  The tool works fine without it using a built-in estimate.

---

## Step 1 — Install it

Open the project folder in VS Code, then open a terminal in that folder
(`Terminal → New Terminal`). Run these one at a time.

**Create an isolated environment** (keeps this project's packages separate):

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Mac / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

After this, your terminal prompt should start with `(.venv)`. That means it
worked.

> **Windows note:** if activation fails with a message about scripts being
> disabled, run this once, answer `Y`, then try the activate line again:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

**Install the tool:**
```powershell
pip install -e ".[dev]"
```

**Confirm it works** (this runs the test suite — no API key needed, costs
nothing):
```powershell
python -m pytest -q
```
You should see something like `27 passed`. If so, you're installed.

---

## Step 2 — Add your Anthropic API key

This tool is **BYOK** ("bring your own key") — you use your own Anthropic
account, and your key never leaves your computer.

1. Go to [console.anthropic.com](https://console.anthropic.com), create an
   account, and generate an API key (it starts with `sk-ant-`). New accounts get
   a few dollars of free credit — plenty for hundreds of résumés.
2. In the project folder there's a file called `.env.example`. **Make a copy of
   it named `.env`** (just `.env`, no other extension).
3. Open `.env` and put your key after the `=`:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```
4. Save it. The tool reads this automatically every time you run it — you only
   do this once.

> **Your key stays private.** The `.env` file is listed in `.gitignore`, so it
> will **not** be uploaded if you push this project to GitHub. Never put your key
> in any other file.

---

## Step 3 — Build your "experience bank"

The tool works from a single structured file (`my_resume.json`) that holds *all*
your experience — more than fits on any one résumé. Think of it as your master
list; the tool picks the best parts for each job.

You have two ways to create it.

### Option A — Parse it from your existing résumés (easiest)

Put 1–3 of your résumé PDFs in the project folder, then run:

```powershell
resume-agent parse Resume1.pdf Resume2.pdf --out my_resume.json
```

This reads your résumés, merges them into one draft, and writes **two** files:
- `my_resume.json` — your draft experience bank.
- `my_resume.review.txt` — **important:** a list of things to check.

**Open the `.review.txt` file and read it.** Because this is your real résumé,
the tool will not silently guess on things that matter. It flags:
- **Contradictions** — if two résumés say different things (e.g. one says you
  "led" a project, another says you "contributed to" it), it asks you which is
  true.
- **Numbers to confirm** — any metric it found ("95% accuracy", "40% faster"),
  so you can verify it's accurate.
- **Strength ratings** — a 1–10 score it suggested for each bullet, which you can
  adjust.

Edit `my_resume.json` to fix anything the review file flagged. **You are the
final say on what's true.**

### Option B — Write it by hand

If you prefer full control, copy the included `my_resume.json` (or the sample in
`tests/fixtures/source_sample.json`) and edit it to your own experience. The
format is human-readable JSON.

**One rule that matters:** any number in a bullet (like "95% accuracy") must be
listed as a structured `metric` with a `display` string that appears word-for-word
in the bullet text. This is what lets the tool guarantee numbers are never
altered. The linter (next step) will tell you if you got this wrong.

### Check your data with the linter

Before generating, run the linter. It catches data problems **before** you spend
any API credits:

```powershell
resume-agent lint --source my_resume.json
```

You want to see: `Lint passed: no data-contract issues found.` If it reports
errors, it tells you exactly which bullet and what to fix (usually a number in
the text that isn't set up as a metric).

---

## Step 4 — Generate a tailored résumé

Save the job posting you're applying to as a plain text file, e.g. `job.txt`
(just paste the posting in — formatting doesn't matter).

Then run:

```powershell
resume-agent generate --source my_resume.json --jd job.txt --out tailored.json
```

This calls Claude (costs ~1–2 cents), tailors your bank to that job, and writes
`tailored.json` — the tailored *content* of your résumé. You'll see
`wrote tailored.json (llm_calls_used=2)` when it finishes.

> Want to see it run without spending anything? Add `--dry-run`. It exercises the
> whole pipeline with a stand-in model (output won't be truly tailored, but it
> proves everything works).

---

## Step 5 — Export to a Word document

Turn that tailored content into an actual résumé file:

```powershell
resume-agent export --input tailored.json --out resume.docx --one-page
```

This writes `resume.docx` — a clean, one-page, ATS-friendly Word document you can
open, tweak, and submit. The `--one-page` flag trims your lowest-priority bullets
if needed to fit one page (it protects a minimum number per section, so it won't
gut your résumé).

> **Tip:** close `resume.docx` in Word before re-running export, or Windows will
> refuse to overwrite it (you'll see a "permission denied" error — that just
> means the file is open).

That's it. Open `resume.docx` and you have your tailored résumé.

---

## Command reference

| Command | What it does |
|---|---|
| `resume-agent parse FILE...  --out my_resume.json` | Build a draft experience bank from résumé PDFs (+ a review file). |
| `resume-agent lint --source my_resume.json` | Check your data for problems before generating. Costs nothing. |
| `resume-agent generate --source my_resume.json --jd job.txt --out tailored.json` | Tailor your bank to a job. Uses your API key. |
| `resume-agent generate ... --dry-run` | Run the full pipeline offline with a stub model (no key, no cost). |
| `resume-agent export --input tailored.json --out resume.docx --one-page` | Render the tailored content to a one-page Word file. |

The typical loop for each new job is just the last two:
```powershell
resume-agent generate --source my_resume.json --jd job.txt --out tailored.json
resume-agent export --input tailored.json --out resume.docx --one-page
```

---

## Tips and tuning

- **One résumé bank, many jobs.** Build `my_resume.json` once. For each new job,
  save a new `job.txt` and re-run `generate` + `export`. The tool re-picks the
  best content for each posting.
- **Coverage report.** `tailored.json` includes a `coverage` section listing job
  keywords your résumé does and doesn't cover. The "missing" list tells you what
  the job wants that you don't have — useful for deciding whether to apply, or
  what real experience to add to your bank.
- **It won't invent missing skills.** If a job wants "AWS" and you don't have it,
  the tool will *not* add it. It lists it as missing. That's the point — add real
  experience to your bank instead.
- **Exact one-page fitting (optional).** Without LibreOffice, the tool *estimates*
  page length. To get exact measurement, install
  [LibreOffice](https://www.libreoffice.org/) — the tool detects it automatically
  and uses it. No configuration needed.
- **Strength scores.** Each bullet in `my_resume.json` has a `strength` value
  (1–10) that boosts your best accomplishments in the ranking. Edit these numbers
  if you disagree with how a bullet is weighted.

---

## Cost

This tool uses your own Anthropic API credits. A single résumé generation costs
roughly **1–2 cents**. Parsing résumés costs a few cents more (it's a bigger
request). New Anthropic accounts include free credit that covers hundreds of
runs. You only pay for what you use, and you can set a spending cap in the
Anthropic console.

Running `lint`, `--dry-run`, and `export` costs **nothing** — they don't call the
API.

---

## Privacy

- **Your API key never leaves your machine.** It's read from your local `.env`
  file and passed directly to Anthropic. It is never stored, logged, or sent
  anywhere else.
- **Your résumé data stays local.** Files like `my_resume.json` and `tailored.json`
  live only on your computer.
- When you run `generate` or `parse`, your résumé content and the job description
  are sent to Anthropic's API (that's how the model tailors them), subject to
  Anthropic's usage policies. Nothing is sent anywhere else.

---

## Limitations (read these)

This tool is honest about what it can and can't guarantee:

- **It verifies attribution, not perfect phrasing.** It guarantees every skill,
  number, employer, and date comes from your data, and that numbers are
  reproduced exactly. It does **not** guarantee a rephrased bullet is a perfect
  paraphrase — so **read your generated résumé before sending it.** You're the
  final check.
- **You must confirm what's true.** When parsing finds contradictions between
  your résumés, it asks *you* to resolve them. It never decides facts about your
  career on its own.
- **"One page" without LibreOffice is an estimate.** It's close, but for a
  guarantee, install LibreOffice or just check the page length yourself.
- **It is not a cover-letter or career-advice tool.** It tailors résumé content
  from your real experience. That's it.

---

*Built as a constrained LLM system: structured experience records, deterministic
relevance scoring, provenance validation, and bounded repair/fallback to generate
job-specific résumés without unsupported claims.*