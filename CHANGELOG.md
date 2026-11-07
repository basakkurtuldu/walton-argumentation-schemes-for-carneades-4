# Changelog

All page numbers refer to Walton, Reed & Macagno (2008), *Argumentation Schemes*, Cambridge University Press ("the book"); section numbers are those of the User's Compendium of Schemes (ch. 9).

## 2026-11-06 — branch `fix/validate-and-correct-schemes`

Baseline: `master` at a7cde94. Checked by loading every file with the Carneades 4 engine (master d19d543): **6 of the 14 scheme files did not load at all** (`walton.yml`, `A_reasoning/2`, `A_reasoning/5`, `B_source-based-arguments/2`, `C_applying-rules-to-cases/2`, `C_applying-rules-to-cases/4`), and in the 8 that loaded the engine's own validator reported 103 scheme problems and 27 language problems; many statements rendered as empty or garbled text. After the changes all 14 files load, `tools/validate_schemes.py` reports 0 errors, and the engine's validator reports only the five inherited range-restriction cases and `true/1` listed under Known limitations in the README.

The changes are ordered from "the file cannot be loaded" to "cosmetic"; each tier is a separate commit, so the later tiers can be dropped if they are not wanted.

### 1. YAML syntax — files could not be loaded (commit "Fix YAML syntax so every file loads")

16 one-line edits: `- id:x` without a space (2), titles containing `: ` that must be quoted (4), list items written `-smaller_part_property(...)` without a space, which YAML reads as a string instead of a list (8), and `assumption:` for `assumptions:` (2), which Carneades ignores silently so the assumptions were lost.

### 2. Statement syntax — statements Carneades' term parser rejects (commit "Make every statement parse and declare its variables")

Carneades drops, with only a message on stderr, every premise, conclusion, assumption or exception it cannot parse, and leaves variables it cannot bind in the statement. Fixed: primed variables `P'`, `W'`, `X'`, `R'`, `Y'` (21, renamed `P2` etc. in the opposition schemes), an unbalanced parenthesis in `needed_nonarbitrary((A,F)`, and three schemes using a variable they did not declare (`part_in_whole`, `verbal_classification_vagueness`, `verbal_slippery_slope`).

### 3. Scheme logic — schemes that do not say what the book says (commit "Correct scheme logic against the book's compendium")

* `division_generic` (10.1, p. 317) was a copy of composition and reasoned from the parts to the whole; now whole → parts, with divisional heredity (CQ1) as the assumption.
* `composition_generic` (9.1, p. 316): the assumption restated the premise instead of CQ1 (compositional heredity).
* `from_example` (6.1, p. 314) and `common_folk_ad_populum` (4.10, p. 313): premise and conclusion were swapped.
* `moral_justification_ad_populum_excuse` (4.6, p. 312) had no conclusion; it was listed as a premise.
* `evidence_hypothesis_falsification` (32.2, pp. 331–332) concluded `¬A`, the negation of its own premise, instead of `¬H`.
* `danger` (37, p. 334) concluded that the danger, not the action, should not be brought about.
* `treat` (35, p. 333): premise 2 is "I am in a position to bring about B", not "position to know"; the title "Argument From Treat" is "Argument From Threat".
* `sacrifice` (20, p. 322): `great_sacrifice(S,A,X)` used an undeclared `X` where the value `V` is meant.
* `abductive_backward` (31.1, pp. 329–330): the premise "A1 is the account that explains D most successfully" was missing; `data_set` had a spurious second argument.
* `opposition-normative` (11.2, p. 318): the major premise is about evaluations, and the minor premise must instantiate its antecedent (`W`). The book prints `W'` in the minor premise; with `W'` the scheme would conclude its own premise false, so this is treated as a misprint.
* `rhetorical_oppositions_normative` (12.1, p. 318): the arguments of `if_treatment_required` were in the wrong order.
* `negative_consequences_prudential`: `strongly_occur` names both the action and the consequence.
* `commitment1`: the conclusion predicate was misspelt (`commined_to`), so it had no template.
* Titles: `opposition-descriptive_3` was labelled "Descriptive Scheme 2"; `verbal_classification_vagueness` carried the definition scheme's title.
* Three schemes existed only in category files and were added to `walton.yml`: `whole_into_parts` (10.2), `negative_consequences_reasoning` (33.3; it had the duplicate id `negative_consequences`), `full_slippery_slope` (53; source added: Walton, *Slippery Slope Arguments*, 1992, pp. 200, 203).

Checked against the book and left unchanged: `fear` (premise 3 is in the book), `bias_ad_hominem`, `full_slippery_slope`'s assumption (= CQ3), `exeptional` (56), and the critical-question coverage of the 24 schemes taken over from Carneades' own `walton.yml`.

### 4. Language templates — what Carneades prints (commit "Make every language template usable and correct its text")

Carneades looks a template up by `name/arity` and fills it with Go's `Sprintf`.

* 29 keys had no arity (`background`, `strongly_occur`, …) and were never found, so the statement text was empty; 0-ary predicates now use `name/0`, the others `name/n`.
* Arity mismatches between key and statements: `cited_bad_consequences`, `conflict_goals`, `position_to_know_group`, `same_meaning`; templates with more `%s` than arguments (`favor/1`, `popular_practise/1`, `other_consequences_presumption/2`) printed `%!s(MISSING)`.
* Malformed verbs: `"% is %s."` (`is/2`), `"%is not required."`, `"% more effectively"`.
* Arguments printed in the wrong roles (`assert_bad`, `help_needed`, `commitment_arises`, `if_treatment_required`, `treatment_required`, `contrary_treatment_required`, `opposite_action`), e.g. "the treatment ⟨subject⟩ is required for the subject ⟨treatment⟩".
* Duplicate keys `biased/1` and `good/1` (YAML keeps the last definition); the first was removed.
* Templates added for the corrected and added schemes; `position_to_know/1`, whose text was "I am in position to bring about %s", renamed `position_to_bring_about/1`.
* Spelling, grammar and stray spaces in about 80 texts ("wil l", "commiued", "Oflicial rulelebooks", " 's", …). This part is cosmetic but was done in the same commit.
* Follow-up in the final commit: ten templates that printed an argument twice via `%[n]s` were rewritten to print each argument once, because Carneades' validator counts `%` characters.

### 5. Titles and sources (commit "Fix typos in titles and sources") — cosmetic

OCR-style errors in titles and references ("lnformal Logic", "Trtatise", "Wayrw Grennan", "Physical Worl", "Ignorence", "Ad Baculum Treat", "Argumentationmustern"), the missing title of `rule_mental_world` and the missing source of `retroductive` (31.5, p. 331).

### 6. Generated category files and tooling

* `tools/validate_schemes.py` (first commit on the branch) and `tools/build_category_files.py` with `categories.yml`.
* The 13 category files are regenerated from `walton.yml`. Before, they were hand-maintained copies that had drifted: `B_source-based-arguments/1` had no language section at all, seven rule schemes appeared in both `C_…/2` and `C_…/4`, `opposition_descriptive_2/3` used different ids from `walton.yml`, and seven schemes of `walton.yml` were in no category file. Membership is otherwise unchanged; `A_reasoning/3`'s second `practical_necessary_condition` is `practical_sufficient_condition` and its second `negative_consequences` is `negative_consequences_reasoning`.

### Not changed

Misspelt identifiers (scheme ids, predicate names, the file name `5_casual-reasoning.yml`) are kept because renaming them changes the interface for existing argument graphs; see `PLAN.md`.
