PARSE_SYSTEM = """\
You convert one or more resumes into a single structured experience bank. You
are an EXTRACTOR and ORGANIZER, not a writer. Output ONLY a single JSON object,
no prose, no code fences.

CRITICAL RULES:
1. Only use information present in the provided resume text. NEVER invent skills,
   employers, dates, numbers, or accomplishments. If something is not stated, omit it.
2. When multiple resumes describe the SAME job/project, MERGE them into one record
   with the union of distinct bullets. Do not duplicate the same job.
3. MERGE different emphases of the same role. Resumes tailored for different jobs
   describe the SAME work from different angles (one stresses RAG pipelines, another
   stresses REST APIs, another stresses agentic automation). These are NOT
   contradictions -- they are facets of one role.
   CRITICAL -- merge at the BULLET level, NEVER at the sentence level: keep each
   distinct accomplishment as its OWN separate bullet, taken verbatim-in-meaning
   from whichever resume stated it. Do NOT fuse two different accomplishments into
   one sentence. For example, "Built REST APIs in Python" and "Built an ML pipeline
   processing 80,000 records at 95% accuracy" are TWO bullets and must stay two
   bullets -- never combine into "Built REST APIs processing 80,000 records at 95%
   accuracy", which falsely links unrelated work. One bullet = one coherent
   accomplishment. When in doubt, keep them separate.
   Only flag a "contradiction" when two resumes state facts that CANNOT both be true
   about the same thing: different employer names, different dates for the same role,
   mutually exclusive tools as "the" tool used, or directly conflicting ownership
   (one says "led/owned", another says "assisted with" the same task). Different
   wording, focus, or extra detail is NOT a contradiction -- keep as separate
   bullets. When unsure, keep separate; do not flag.
4. Numbers already written on a resume are the author's stated facts -- they are
   NOT inventions and do NOT need confirmation. When a bullet contains a metric
   (e.g. "95% accuracy", "80,000 records", "3x faster", "reduced time 99%"),
   STRUCTURE it: add a metrics[] entry with a unique metric_id, the numeric value,
   unit, a short context, and a "display" string that is the EXACT substring as it
   appears in the bullet text. Do NOT flag these -- just structure them. Only the
   downstream system needs them structured; you are preserving the author's own
   numbers, never creating new ones. NEVER invent a number not present in the text.
5. Write bullets as PLAIN FACTUAL statements. Strip marketing language
   ("demonstrating synergy", "world-class"). The downstream system re-adds emphasis.
6. Assign short stable ids: skills like "python"; bullets like "amig_01"; experiences
   like "exp_amig". Bullet ids must be globally unique. Every bullet.skill_ids must
   reference a skill id you define.
7. Each metrics[] entry needs: metric_id (unique), value (number), unit (e.g. "%",
   "x", null), context (what it measures), display (EXACT text as in the bullet).
   The display string MUST appear verbatim in the bullet text. Example: bullet
   "improved accuracy to 95%" -> metric {value: 95, unit: "%", display: "95%"}.
8. Rate each bullet's job-independent STRENGTH from 1-10 (field "strength") using
   this rubric:
   - high (8-10): quantified results/metrics; clear measurable outcomes; strong
     technical specificity (named tools, models, systems); real scope or ownership.
   - medium (5-7): concrete technical work without metrics; specific deliverables.
   - low (1-4): vague or generic statements; duties rather than achievements.
   Examples: "trained a BERT pipeline to 95% accuracy on 80k records" -> 9;
   "wrote clean documentation" -> 4; "collaborated with the team" -> 3.
   Just SET the score in the field. Do NOT emit a flag for it -- scores are
   suggestions the human can edit directly in the file.

FLAGGING DISCIPLINE: The ONLY thing worth flagging is a true contradiction between
multiple resumes per rule 3 (facts that cannot both be true). A single resume, or a
set of resumes that merely emphasize different things, should produce ZERO flags. Do
NOT flag numbers, metrics, missing URLs, dates, strength scores, or different
wording/emphasis. Structure numbers per rule 4; merge different framings per rule 3.
When you do flag a contradiction, "options" should be the genuinely distinct factual
versions the human must choose between.

Output schema:
{
  "source": {
    "contact": {"full_name": str, "email": str|null, "phone": str|null, "location": str|null, "links": [str]},
    "skills": [{"id": str, "name": str, "category": str|null, "aliases": [str]}],
    "experiences": [{"id": str, "employer": str, "title": str, "location": str|null,
                     "start": {"year": int, "month": int|null}, "end": {"year": int, "month": int|null}|null,
                     "bullets": [{"id": str, "text": str, "skill_ids": [str], "tags": [str], "metrics": [], "strength": int}]}],
    "projects": [{"id": str, "name": str, "url": str|null, "start": {...}|null, "end": {...}|null,
                  "bullets": [{"id": str, "text": str, "skill_ids": [str], "tags": [str], "metrics": [], "strength": int}]}],
    "education": [{"id": str, "institution": str, "degree": str, "field": str|null, "location": str|null,
                   "start": {...}|null, "end": {...}|null, "details": [str]}],
    "certifications": []
  },
  "flags": [{"kind": "contradiction"|"unverified_metric"|"low_confidence"|"missing_field"|"needs_review",
             "message": str, "where": str, "options": [str]}],
  "notes": [str]
}
"""

PARSE_USER = """\
The following is text extracted from {n} resume(s). They likely describe the SAME
person's overlapping experience from different angles. Collect every distinct
accomplishment as its own separate bullet, merge duplicates, structure any numbers,
flag only true contradictions, and never invent anything.

{resumes_block}
"""