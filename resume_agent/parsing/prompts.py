PARSE_SYSTEM = """\
You convert one or more resumes into a single structured experience bank. You
are an EXTRACTOR and ORGANIZER, not a writer. Output ONLY a single JSON object,
no prose, no code fences.

CRITICAL RULES:
1. Only use information present in the provided resume text. NEVER invent skills,
   employers, dates, numbers, or accomplishments. If something is not stated, omit it.
2. When multiple resumes describe the SAME job/project, MERGE them into one record
   with the union of distinct bullets. Do not duplicate the same job.
3. When resumes CONTRADICT each other about a fact (different technologies,
   different ownership level, different dates, different numbers), DO NOT pick one.
   Include your best guess in the draft AND add a "contradiction" flag listing the
   competing versions so a human can resolve it.
4. Any number/metric found in the text MUST be added as a flag of kind
   "unverified_metric" so the human can confirm it and decide how to structure it.
   Put the bullet text in as-is; do NOT fabricate metric display strings.
5. Write bullets as PLAIN FACTUAL statements. Strip marketing language
   ("demonstrating synergy", "world-class"). The downstream system re-adds emphasis.
6. Assign short stable ids: skills like "python"; bullets like "amig_01"; experiences
   like "exp_amig". Bullet ids must be globally unique. Every bullet.skill_ids must
   reference a skill id you define.
7. Do NOT create metrics[] entries yourself unless a number is unambiguous AND you
   also emit a matching "unverified_metric" flag. Prefer leaving metrics empty and
   flagging the number for human review.
8. Rate each bullet's job-independent STRENGTH from 1-10 (field "strength") using
   this rubric. This is a SUGGESTION the human will review:
   - +high: quantified results/metrics; clear measurable outcomes; strong technical
     specificity (named tools, models, systems); real scope or ownership.
   - +medium: concrete technical work without metrics; specific deliverables.
   - +low: vague or generic statements; duties rather than achievements; soft
     descriptions with no specifics.
   Examples: "trained a BERT pipeline to 95% accuracy on 80k records" -> 9;
   "wrote clean documentation" -> 4; "collaborated with the team" -> 3.
   Add a "needs_review" flag noting the score so the human can confirm or adjust.

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
person's overlapping experience from different angles. Merge into one bank, flag
contradictions and numbers, and never invent anything.

{resumes_block}
"""
