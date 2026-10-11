# goodhart — build & evidence-status note (2026-10-11)

## What exists now

`paper/main.tex` + `paper/refs.bib` compile clean with TinyTeX
(`pdflatex` → `bibtex` → `pdflatex` ×2, exit 0, no undefined citations or
references, 17 bibitems, 6 pages). Build is non-deterministic run-to-run only
in PDF timestamps; source hashes are pinned in `paper/BUILD_20261011.sha256`:

```
4e72929ec55d2ff46b17af943137b94432881b229c545580b15b6f70eb71059d  main.pdf
0321bf6033d16852ce4110ae21b224a39d1c774123b2591f1bd527edee4254f9  main.tex
8f8b381a37b3efc9031afbba717cbc5778f714a525c18792ef3a769c6a32a4b3  refs.bib
```

Reproduce with:

```bash
export PATH="$HOME/.local/bin:$PATH"     # TinyTeX
cd goodhart-project/paper
pdflatex -interaction=nonstopmode main.tex && bibtex main && \
pdflatex -interaction=nonstopmode main.tex && \
pdflatex -interaction=nonstopmode main.tex
```

## Numbers in the paper and where they come from

| Paper claim | Landed artefact |
|---|---|
| C.2 table, six α levels, true/CI/proxy/detach | `c2/results/table1_true_score.csv` (verbatim) |
| per-seed raw records | `c2/results/summary.csv` |
| α=0.5 / α=1.0 abstract numbers | same table, rows 1–2 |
| preregistered decision rule, power cap 44.6, paired diffs 446.2±15.1 / 432.7±16.0 | `prereg/preregistration_c2.md` L81–L98 |
| ETL table, step_acc / parse_ok / first_err_median | `etl/results/table_detach.csv` (verbatim) |
| gate PASS because accuracy is 0 | `etl/results/gate_run.log` (three families CLEAN) |
| replay mismatch = 0 over 614 steps | `etl/results/` replay log |
| Q5 both arms true≈499.99, steps_alive=500.0, mean_speed≈0.107 | `q5/results/summary_q5.csv` |
| Q5 null attribution to option (a) | `prereg/preregistration_q5.md` L48–L54, L67–L76 |
| one model / temperature 0 / timeout 60s / one retry | `src/ollama_model.py` L8, L26, L38 (HANDOVER §13.13) |

**The figure is deliberately not included.** `c2/results/fig1_detach_curve.pdf`
exists but the paper cites no value from it, so an early version of this draft
referenced it and then the reference was removed rather than leave a figure
whose only role was decoration. If it is added back, it must be because a
sentence points at a specific feature of it.

## Citation status (changed today — the draft's own claim was stale)

`docs/HANDOVER.md` §13.4 and `PAPER_DRAFT/OUTLINE.md` both still say
"13 filled / 4 empty". **That is out of date.** Auditing
`prereg/citation_verification.csv` today gives **17/17 filled, 0 empty**, all
`verified=✅` (13 on 2026-10-07, 4 more on 2026-10-08, including the four that
the HANDOVER describes as deliberately left blank).

Independent verification performed today, beyond trusting the ✅ column:

- `reference_checker` over all 17 entries → **14 found, 3 partial, 0 not_found**
- arXiv API `id_list=1606.06565` → "Concrete Problems in AI Safety", published
  2016-06-21, six author names verbatim match
- Crossref `10.1002/(SICI)1234-981X(199707)5:3<305::AID-EURO184>3.0.CO;2-4` →
  title/container/year/volume/issue/page/authors all verbatim match
- Crossref `10.1007/978-1-349-17295-5_4` → "Problems of Monetary Management:
  The UK Experience", 1984, book-chapter, pp. 91–121, author C. A. E. Goodhart

The 3 partials were re-checked and are fine; they were partial only because
the index matched a different record (e.g. Strathern → "Partial Connections"
review; Amodei → "AI Safety Gridworlds"), not because the cited work is wrong.

## Residual defects disclosed in the paper (do not silently fix)

1. `zotero_key` unfilled for all 17 rows; `tools/reconcile_zotero.py` not run.
2. `goodhart1975problems` is cited as the **1984 Macmillan reprint** chapter
   (pp. 91–121). Original 1975 pagination not located. The popular short form
   "When a measure becomes a target, it ceases to be a good measure" is
   Strathern 1997 paraphrasing Hoskin 1996 — **not Goodhart's own words**.
3. The project's "three cracks" taxonomy has **no external counterpart**. The
   closest work (Manheim & Garrabrant 2018, arXiv:1803.04585) has **four**
   categories (regressional/extremal/causal/adversarial). The three cited laws
   are therefore cited as laws, never as the source of a three-way split.
4. Year-column convention: `year` = publication year, preprint year (if
   different) goes in `venue`. Affected: `ross2011reduction` (2011 vs 2010),
   `sainz2024nlp` (2024 vs 2023), `morris2024levels` (2024 vs 2023).
5. `fig_error_decomp.pdf` is referenced in §4.3 as having "the shape of a floor
   and not the shape of a mechanism". Its values are **not** quoted.

## What the paper still needs before any submission

- **Venue decision.** Current target per `PAPER_DRAFT/OUTLINE.md` is a
  Safe RL / Safe Control workshop. At 6 pages with five seeds on CartPole and
  one model at temperature 0, this is a workshop paper, not a main-conference
  paper.
- **A non-floor rerun of the ETL pipeline.** The two analyses it was built for
  (error-recovery trigger conditions, short-to-long chain extrapolation) are
  blocked by the floor, not by the design. This is a measurement rerun.
- **HANDOVER.md §13.4 and OUTLINE.md must be corrected** to say 17/17, not
  13/4 — otherwise the paper cites a stale internal count.
- `\todo{}`, `\exploratory{}`, `\tbd{}` macros are defined and currently used
  only by `\exploratory{}` (§4.3 head) and nowhere else. Verify none survive
  into a submission.

## Pointer fix (2026-10-12, numbers untouched)

The paper cited `docs/HANDOVER.md` by line number; after the working tree
gained §13.13 (+82/−19) every one of those lines shifted by ~50, so all four
HANDOVER pointers were stale (L581–594, L606–618 ×2, L682, L716–721).
Mechanical audit of every number in main.tex against the landed artefacts
found **zero numeric discrepancies** — both tables are verbatim against
`c2/results/table1_true_score.csv` and `etl/results/table_detach.csv`, and the
abstract/bullet figures re-derive from the same CSVs (min/max detach
86.6%–100.5%, proxy max 1.3762→1.38, per-family steps 197/204/213 = 614,
0/90 fully-correct tasks re-scored through `Validator.check_step`).

Fix: HANDOVER refs now cite the **section** (§13.11 for the C.2 adjudication
and final wording, §13.13 for the floor-effect statement) instead of line
numbers, and the model-config ref points at the authoritative artefact
`src/ollama_model.py` (L8 timeout/retry, L26 `__UNTESTED__`, L38 temperature)
rather than a HANDOVER line. Rebuilt 2026-10-12 (4 passes, exit 0, no
undefined refs, 17 bibitems, 6 pages); hashes above refreshed, `refs.bib`
unchanged.

Known-stale pointer left in place on purpose: `docs/HANDOVER.md` §13.13 still
says "correct 0/614", superseded by the 5/614 re-score (see
`PAPER_DRAFT/OUTLINE.md` §3.3 note "已 superseded"); HANDOVER is kept as a
historical session record per that decision, and the paper quotes 5/614.
`PAPER_DRAFT/OUTLINE.md` and `CLAIM_LEDGER.md` still contain several stale
HANDOVER line pointers of the same kind — not fixed here (working notes, not
the deliverable), listed for a later sweep.
