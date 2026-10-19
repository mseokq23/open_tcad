# Specs

A spec is the contract between the four agent roles. **No physics code without a merged spec.**

| Folder | Spec kind | ID pattern | Example |
|---|---|---|---|
| `models/` | One physics model: equations, parameters, validity, numerics | `MOD-<AREA>-<NNN>` | `MOD-RG-001` (SRH) |
| `verification/` | One verification case: device, inputs, reference, tolerance | `VER-<AREA>-<NNN>` | `VER-PN-001` |
| `materials/` | Material parameter set and how values were chosen | `MAT-<MAT>-<NNN>` | `MAT-SI-001` |

Areas: `DD` core transport, `MOB` mobility, `RG` recombination/generation, `BGN` bandgap
narrowing, `STAT` statistics, `II` impact ionization, `BTBT` band-to-band tunneling,
`CON` contacts, `DOP` doping, `MESH`, `CONV` convergence, `PN` junction cases, `MOS`, `GUI`.

The file name is the ID (`models/MOD-RG-001.md`). Start from [`TEMPLATE.md`](TEMPLATE.md).

## Lifecycle (`status:` in the front matter)

```
draft ──► reviewed ──► implemented ──► verified
  ▲  researcher   verifier       implementer     verifier
  └──────────── any role can send it back with a comment ────────────┘
```

* **draft**: written by the researcher from primary sources. Every equation and parameter has a
  locator (equation/table/page). `TBD` locators are allowed only in drafts.
* **reviewed**: the verifier re-derived or re-read every equation and parameter from the cited
  source *independently* (two-key rule, docs/literature-policy.md) and agreed.
* **implemented**: code merged, `implemented_in:` filled, unit tests pass.
* **verified**: the verification specs listed in `verified_by:` pass at their stated tolerance in CI.

`scripts/check_citations.py` checks front matter, source ids and locators; `--strict` (phase
gates) fails on any `TBD` locator or any status below `verified` for models in the release.

`bootstrap: true` marks the four phase-0 specs written together with the scaffold (MOD-DD-001,
MOD-RG-001, MOD-MOB-000, MOD-DOP-001). They are implemented and covered by VER-PN-001, but their
locators and independent review are still pending (backlog P1-SPEC-001, P1-VER-001). The checker
only warns about their `TBD`s; `--strict` fails until the flag is removed after review.
