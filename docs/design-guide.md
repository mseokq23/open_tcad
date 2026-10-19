# Design guide (GUI)

Owner: designer role. Reviewed through screenshots (`scripts/snapshot_gui.py`) and the
`gui-critic` subagent.

## 1. Principles
1. **Follow the TCAD workflow, not a vendor's look.** Structure → Mesh → Physics → Simulation →
   Results is a generic, industry-wide sequence; arrange the UI around it. Do not imitate any
   commercial tool's layout details, icons, names or command syntax.
2. **Show provenance.** Every model and material value shown in the GUI displays its source and
   status (`needs-source`, `extracted`, `checked`, `conflict`) — this is the product's
   differentiator.
3. **Never block the window.** Long work runs in the worker process; the UI shows progress,
   allows cancel, and streams the log.
4. **Reproducible by construction.** Every GUI action edits the project file; a run can be
   reproduced from the CLI with the same file.
5. **Errors are actionable.** Convergence failures name the bias point and suggest the next
   step (smaller step, different initial guess, finer mesh).

## 2. Layout
* Left: project tree (workflow steps and objects). Center: tabbed workspace (Structure, Mesh,
  Results). Right: property inspector for the selection. Bottom: log and run queue. Status bar:
  solver, run state.
* Minimum window 1280x800; docks resizable; layout state persisted per user.

## 3. Visual system
* Use the platform's native Qt style; add a small token set (spacing 4/8/12/16/24 px, one accent
  colour, semantic colours for status: checked = green, extracted = blue, needs-source = amber,
  conflict = red), defined once in `gui/theme.py` (P1-DES-001).
* Typography: system UI font; monospace for numbers in tables and the log.
* Plots: consistent axis labels with units; log scale for currents and densities; colour-blind-safe
  palette; no chart junk.
* Light and dark themes both pass contrast checks (WCAG AA for text).

## 4. Screenshot review loop (designer)
1. Implement the change.
2. `uv run python scripts/snapshot_gui.py --out docs/design/snapshots/<feature>.png`
   (add `--state` options as views grow).
3. Read the PNG yourself, then ask the `gui-critic` subagent for an independent critique against
   this guide.
4. Fix the top findings; repeat at most 3 rounds; commit the final snapshot with the PR.

## 5. Accessibility and usability checklist
Keyboard navigation for every action; tooltips with units; no information only by colour;
readable at 125 % scaling; undo/redo for structure edits; destructive actions confirm.
