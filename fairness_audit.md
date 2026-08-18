# Fairness / Bias Audit — CV Matching Pipeline

## Why this exists

TalentiniHR ranks candidates against jobs using semantic similarity between
CV text and job descriptions (`sentence-transformers`, cosine distance via
pgvector). Embedding models are trained on large, uncurated text corpora and
can encode real-world biases present in that data. Before treating this
pipeline's rankings as a meaningful signal for hiring decisions, it's worth
directly testing whether it penalizes candidates for things that have
nothing to do with their actual qualifications.

This audit checks four dimensions, each chosen because it's a documented
axis of bias in real-world hiring:

1. **Employment gaps**
2. **Non-traditional education** (bootcamp vs. CS degree)
3. **Gendered wording** in resume language
4. **Name-based signals** correlated with race/ethnicity

## Methodology

For each dimension, synthetic CV pairs were constructed that are **identical
in substance** — same skills, same years of experience, same job titles,
same companies — but differ in exactly one target variable. Each CV was run
through the real pipeline (`parse_cv` → `build_candidate_embedding_text` →
`embed_text`) and scored via cosine similarity against a single fixed,
generic job description ("Software Engineer... Python, REST APIs, cloud
infrastructure, and databases..."). If the pipeline is fair on a given
dimension, the two scores in a pair should be nearly identical; a
consistent, meaningful gap suggests the model is using that variable as an
unintended proxy signal.

Name pairs for dimension 4 come from Bertrand & Mullainathan (2004), *"Are
Emily and Greg More Employable Than Lakisha and Jamal?"* — a well-known
resume-callback study using names empirically associated with different
racial groups in U.S. hiring contexts. Gendered wording in dimension 3 is
based on Gaucher, Friesen & Kay (2011), *"Evidence That Gendered Wording in
Job Advertisements Exists and Sustains Gender Inequality,"* which documents
masculine-coded (e.g. "competitive," "dominant," "decisive") vs.
feminine-coded (e.g. "collaborative," "supportive," "committed") language
patterns.

Script: `scripts/fairness_check.py`. Standalone, no DB required — run with
`python -m scripts.fairness_check`.

## Results

| Dimension | Variant A | Variant B | Delta (A − B) |
|---|---|---|---|
| Employment gap | No gap: 0.6377 | 2-year gap: 0.6564 | −0.0187 |
| Education pathway | CS degree: 0.6184 | Bootcamp: 0.5965 | **+0.0219** |
| Gendered wording | Masculine-coded: 0.6614 | Feminine-coded: 0.6723 | −0.0109 |
| Name signal (female-coded) | Emily: 0.5684 | Lakisha: 0.6103 | **−0.0418** |
| Name signal (male-coded) | Greg: 0.5886 | Jamal: 0.5834 | +0.0052 |

All deltas are small in absolute terms. For context, a genuinely relevant
vs. irrelevant candidate pairing (see `tests/test_matching.py`, DevOps vs.
Marketing background against a DevOps job) produces a much larger gap —
these fairness-dimension deltas are an order of magnitude smaller than real
matching signal, which is reassuring. That said, "smaller than the main
signal" is not the same as "safe to ignore," particularly for the two
flagged results below.

## Interpretation

**Employment gap (−0.0187):** No meaningful penalty observed. If anything
the gap version scored marginally higher, almost certainly noise at this
magnitude.

**Education pathway (+0.0219):** The CS-degree CV scored consistently
higher than the otherwise-identical bootcamp CV. This is the most
plausible finding of the four — small, but directionally consistent with
a known concern about embedding models favoring traditionally-credentialed
language. Worth taking seriously, though a single pair isn't enough to
call this conclusive on its own.

**Gendered wording (−0.0109):** Likely **confounded**, not a clean
finding. The job description contains the literal word "team," and the
feminine-coded CV variant also uses the word "team" ("...considerately
with the team..."), while the masculine-coded variant doesn't. This is a
plausible alternative explanation for the entire delta — a keyword overlap
artifact rather than evidence of gender-coding sensitivity. This test would
need to be rebuilt with strictly parallel sentence structure (matching
word count and unrelated vocabulary) before drawing any real conclusion.

**Name signal (−0.0418 for Emily/Lakisha, +0.0052 for Greg/Jamal):** The
largest single delta measured, but **inconsistent** across the two name
pairs — if this reflected a systematic bias by race, both pairs would be
expected to skew the same direction. They don't. With one CV template per
name, this can't distinguish "real, systematic effect" from "embedding
noise specific to these particular tokens." This is a genuine limitation
of an n=1-per-condition test, not a resolved finding either way.

## Known confound / open issue: skill extraction inconsistency

While building this audit, the education-pathway pair surfaced a
concerning inconsistency **independent of the fairness question**: the
CS-degree CV and the bootcamp CV have an *identical* `Skills:` section
text, but `parse_cv` detected 5 skills for one and 6 for the other. Since
`build_candidate_embedding_text` prepends detected skills to the embedding
input, inconsistent extraction on identical input text is itself a
pipeline bug that could be contributing to (or masking) fairness-relevant
score differences, separate from anything the embedding model itself is
doing. This needs to be root-caused before the fairness numbers above can
be fully trusted — see open follow-up.

## Limitations of this audit

- **Single CV pair per dimension** (two pairs for the name dimension). This
  is a targeted diagnostic, not a statistically powered study — it can
  surface plausible concerns worth investigating, not prove or disprove
  bias conclusively.
- **One fixed job description.** Effects could differ against other job
  types/domains; not tested here.
- **One embedding model** (`all-MiniLM-L6-v2`). Findings are specific to
  this model and may not generalize to others.
- **The gendered-wording test has a known confound** (see above) and
  should be rebuilt with tighter controls before being treated as evidence
  either way.

## Recommended mitigation

Regardless of how conclusive each individual finding is, one low-cost,
high-value mitigation is available: **strip the candidate's name from the
text used to generate the embedding.** Currently
`build_candidate_embedding_text` embeds the full raw CV text, which
includes the name line (typically the first line, per `pick_name`'s
heuristic). Since the name has no bearing on qualification, removing it
from the embedding input (while still storing and displaying it normally
elsewhere) closes off name-based signal as a possible influence on
matching scores entirely, rather than just measuring how much it currently
matters.

## Follow-ups

- [ ] Root-cause the skill-count inconsistency on identical `Skills:` text
      (see "Known confound" above)
- [ ] Rebuild the gendered-wording test with strictly parallel sentence
      structure to remove the keyword-overlap confound
- [ ] Implement name-stripping before embedding generation
- [ ] Re-run this audit after the above fixes, to see whether deltas shrink