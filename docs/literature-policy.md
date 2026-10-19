# Literature policy

The simulator is only as trustworthy as its numbers. This policy makes every equation and
parameter traceable and independently confirmed.

## 1. Source hierarchy
1. **Primary sources**: the original paper or measurement report where the model or value was
   first published (peer-reviewed journals, conference proceedings with DOI, standards).
2. **Authoritative monographs/textbooks** with ISBN (e.g. `sze-ng-2007`, `selberherr-1984`), for
   textbook results and when they reproduce a primary source faithfully (cite both).
3. **Curated databases** (e.g. the Ioffe NSM archive) as pointers: use them to find the primary
   source; cite them only when the primary source is unavailable, and say so in `notes`.
4. **Not acceptable as sources:** vendor TCAD manuals, unreferenced web tables, forum posts,
   AI-generated text, your own memory.

Open-source simulators (DEVSIM examples, Charon, Genius-TCAD-Open) may be read to understand
numerics, never as the source of a physical value, and GPL code is never copied.

## 2. What a citation needs
* A reference entry in `src/opentcad/data/references.yaml` with DOI (articles), ISBN or DOI
  (books) or URL + access date (web/datasets). Create it with
  `uv run python scripts/doi_lookup.py <doi>`, which reads the metadata from Crossref.
* A **locator** for every equation and value: equation number, table and row, figure, or page.
  "the paper" is not a locator. Chapter-level locators are allowed only for textbook results
  and must name the section.
* Units exactly as published, then the conversion to the project's units (cm, s, V, K) written
  out in the spec.

## 3. Status of a parameter (`data/materials/*.yaml`)
| Status | Meaning | Who sets it |
|---|---|---|
| `needs-source` | no acceptable source read yet; `value: null`, `candidates` listed | researcher |
| `extracted` | read at `locator` in `source` by one reader (`extracted_by`) | researcher |
| `checked` | an independent second reader found the same value (`checked_by`) | verifier |
| `conflict` | sources disagree beyond their stated uncertainty; ≥ 2 candidates | researcher → human decides |

The code enforces this: `MaterialDB.value(..., policy="dev")` accepts `extracted`/`checked`;
`policy="strict"` (phase gates) accepts only `checked`. A caller may pass an explicit
`override`; that value is then the caller's input, documented where it is passed.

## 4. Two-key rule
The verifier re-reads each new equation and value **blind**: the `source-checker` subagent
receives only the source id, locator, quantity description and expected unit, never the
claimed value. Exact agreement → `checked`. Disagreement → request changes with both readings
and page images or quotes of the locator. The extractor never checks its own work.

## 5. Access to papers
* Prefer open-access versions (arXiv, publisher open access, institutional repositories).
* Paywalled papers: the human places the PDF in `literature/pdfs/<reference-id>.pdf`. The
  folder is git-ignored (copyright) and copied into every agent worktree via `.worktreeinclude`.
* If a source cannot be opened, do not fill the value: leave `needs-source`, label the issue
  `status:needs-human`, and say exactly which document is needed.

## 6. Copyright
Equations and numerical values are facts and are transcribed with citation. Do not copy prose,
figures or tables wholesale; at most a short phrase in quotes when wording matters. Never
commit PDFs.

## 7. Conflicts and uncertainty
When sources disagree, record every candidate with its source, locator and stated
uncertainty, set `conflict`, and explain the difference (temperature, doping range, measurement
method). The human chooses; the decision and its reason go into the spec's review log.
