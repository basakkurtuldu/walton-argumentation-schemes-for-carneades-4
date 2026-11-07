# Plan for future work

Status on 2026-11-06 (branch `fix/validate-and-correct-schemes`): all 14 scheme files load in Carneades 4; `tools/validate_schemes.py` reports 0 errors and 30 warnings. What follows is what is still open, roughly in order of value.

## 1. What Carneades' own validator still reports

Running the engine's `validation` package over the files gives, apart from test artefacts:

* `ad_hominem` (S), `practical_necessary_condition` and `practical_sufficient_condition` (A2, P), `regulative_rule` (A), `sorites_slippery_slope` (A): "variable not used in premises or deletions" and "variable declared but not used". These follow the book (e.g. 55.3 concludes "S must do A" with S appearing nowhere else), but the GoCHR inference engine needs every variable of a conclusion, assumption or exception to be bound by a premise. Options: (a) add an agent premise (e.g. `agent(A)`), which changes the scheme's variables and therefore the parameters existing graphs pass; (b) drop the unbound variables from the assumption/exception statements (`conflict_goals(P,A2,A)` → `other_goals_conflict(A)`, `possible_agent(X,P)` → `possible_action(X)`); (c) accept. Decide per scheme; (b) is the smallest change for the practical-reasoning pair.
* `true/1` is "not a predicate symbol" because `true` parses as a boolean. Rename the predicate (e.g. `is_true/1`) together with the identifier clean-up below.

## 2. Identifier clean-up (one coordinated commit, with a mapping table)

Renaming changes the interface for argument graphs that instantiate these schemes, so do it once, document the old → new mapping, and bump a version: scheme ids `exeption_to_rule`, `exeptional`, `epistemic_ignorence`, `popular_practise`, `treat`, `opposition-descriptive_1/2/3`, `opposition-normative` (hyphens; the GoCHR rule name is built from the id, so check it round-trips through the CHR parser); predicate names `recieves_evaluation`, `cannot_recieve_evaluation`, `oficcial_rulebook`, `succesful_account`, `succesful_diagram`, `certainity_no_need`, `individuals_propoerty`, `not_has_propery`, `vaguness_recejted`, `beyond_contetion`, `situation_necessiy`, `posible`, `all_parts_propert`, `character_revelant`, `arguement_not_accepted`, `easy_to_achive`, `commited_opposite`, `evidence_not_commited`; file name `A_reasoning/5_casual-reasoning.yml` → `5_causal-reasoning.yml` (also update `categories.yml`).

## 3. Critical-question coverage, scheme by scheme

Only the schemes touched in this round were checked line by line against the book. A full pass should, for each of the 114 schemes, compare premises, conclusion, assumptions (CQs that hold until questioned) and exceptions (CQs presumed false until proven) with the compendium, and record the page in `meta.source`. Known gaps: `retroductive` lacks CQ1–CQ3; several schemes carried over from Carneades' `walton.yml` (`expert_opinion`, `position_to_know`, `cause_to_effect`) model fewer CQs than the book lists; 0-ary statements (`background`, `being_credible`, `accept_saying`, …) could be given variables.

## 4. Negation in the language

Carneades prints `¬p(a)` as the raw term because `Language.Apply` does not recurse into `¬`. Either add a `¬/1` template (`"It is not the case that %s."`, which still shows the inner term raw) or propose a change to the engine that applies the language to the argument of `¬`.

## 5. Make the engine-level check part of the repository

The check that produced the numbers in `CHANGELOG.md` is a small Go program (`schemecheck`) that, for every file: imports it with `encoding/yaml.Import`, runs `validation.Validate`, instantiates every scheme with constant parameters (`InstantiateScheme`), inspects every statement text for empty strings and `%!` Sprintf artefacts, and translates every scheme into a GoCHR rule with `RuleStore.AddRule` to surface the errors `TheoryToRuleStore` drops. It needs Go, the carneades-4 sources and `gopkg.in/yaml.v2`. Add it under `tools/go/` with a `go.mod` that uses `replace` directives, and a GitHub Actions workflow that runs `validate_schemes.py`, `build_category_files.py --check` and `schemecheck`.

## 6. Upstream

Offer the syntax, logic and template corrections (tiers 1–4 of `CHANGELOG.md`) to the original repository, and the three corrected Carneades-era schemes (`danger`, `treat`, `evidence_hypothesis_falsification` are this repository's; `walton.yml` in carneades-4 itself is unaffected) where applicable. The book errata found on the way (10.1/9.1 CQ glosses transposed on pp. 316–317; `W'` in the minor premise of 11.2) could be reported to the publisher.

## 7. Documentation

Add to the README, per category file, the list of scheme ids and book sections; add an example argument graph per category that instantiates each scheme (also usable as a regression test with the Carneades CLI).
