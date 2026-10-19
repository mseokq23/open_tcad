# Literature

| Folder | Tracked in git | Contents |
|---|---|---|
| `pdfs/` | **no** (copyright) | Source documents the human provides: `pdfs/<reference-id>.pdf`, named after the id in `src/opentcad/data/references.yaml`. Copied into every agent worktree via `.worktreeinclude`. |
| `notes/` | yes | Researcher reading notes: `notes/<reference-id>.md` — what was read where (page, table, equation), unit conventions, doubts. Never paste long passages of the source. |

How a paywalled paper gets in:
1. An agent labels its issue `status:needs-human` and names the document (authors, title, year, DOI).
2. You obtain it legally (library, publisher access) and save it as `literature/pdfs/<reference-id>.pdf`
   in the **main checkout**. Worktrees created afterwards get a copy automatically; for an
   existing worktree, copy the file there as well.
3. Remove `status:needs-human`, add `status:ready` again; the orchestrator re-dispatches the item.

The verifier's `source-checker` subagent may read only `literature/pdfs/` in this repository (enforced
by `scripts/hooks/blind_read_guard.py`), so notes and data never leak the value it is checking.
