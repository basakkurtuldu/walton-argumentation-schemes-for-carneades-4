
# Walton Argumentation Schemes for Carneades 4

This repo contains full lists of **Walton's Argumentation Schemes** in YAML for the use for the [**Carneades Argumentation System** (version 4)](https://github.com/carneades/carneades-4).

25 of the **Walton's argumentation schemes** are already available in YAML at **Carneades 4** as [walton.yml](https://github.com/carneades/carneades-4/blob/master/examples/AGs/YAML/walton.yml). However, in [**Argumentation Schemes (2008)**](https://www.cambridge.org/core/books/argumentation-schemes/9AE7E4E6ABDE690565442B2BD516A8B6), there are a total of **106 argumentation schemes**. We aimed to complete the list and created the remaining 81 argumentation schemes in YAML.

In addition to our main file [walton.yml](walton.yml) in which a complete list is presented, there are also smaller files which are classified based on the classification system present in [**Argumentation Schemes (2008)**](https://www.cambridge.org/core/books/argumentation-schemes/9AE7E4E6ABDE690565442B2BD516A8B6). First, all the schemes are divided into 3 main categories ([**Reasoning**](A_reasoning), [**Source-based Arguments**](B_source-based-arguments), [**Applying Rules to Cases**](C_applying-rules-to-cases)), and under those categories, different files are created corresponding to different types of arguments falling into each category.

This study was conducted within the scope of the master's thesis titled **Douglas Walton's Argumentation Schemes and Applications** prepared by [**Başak Kurtuldu**](https://github.com/basakkurtuldu) under the supervision of [**Dr. Vedat Kamer**](https://istanbul.academia.edu/VedatKamer), in the [**Department of Philosophy**](http://felsefe.edebiyat.istanbul.edu.tr), [**Istanbul University**](https://www.istanbul.edu.tr). This fork of the [original repository](https://github.com/basakkurtuldu/walton-argumentation-schemes-for-carneades-4) corrects errors in the files; see [CHANGELOG.md](CHANGELOG.md) for what changed and [PLAN.md](PLAN.md) for what remains open.

## Files

* `walton.yml` – the complete list (114 schemes). **This is the only hand-edited scheme file.**
* `A_reasoning/`, `B_source-based-arguments/`, `C_applying-rules-to-cases/` – one file per type of argument. These files are **generated** from `walton.yml`: each contains, copied verbatim, the schemes assigned to it in `categories.yml` and exactly the language templates those schemes use, so each file loads into Carneades 4 on its own. Do not edit them; edit `walton.yml` (or the grouping in `categories.yml`) and run `python3 tools/build_category_files.py`.
* `categories.yml` – which scheme goes into which category file.
* `tools/validate_schemes.py` – checks the files against the rules Carneades 4 applies when it loads a theory (see below).
* `tools/build_category_files.py` – regenerates the category files; `--check` reports stale files without writing.

## Checking the files

```
python3 tools/validate_schemes.py            # 0 errors expected; warnings are informational
python3 tools/build_category_files.py --check
```

Both need Python 3 and PyYAML. The validator follows the Carneades 4 source (`src/engine/caes/caes.go`, `src/engine/caes/encoding/yaml/yaml.go`, `src/engine/validation/validation.go`):

* every file must parse as YAML with an `argument_schemes` list, and a scheme may only use the keys Carneades reads (`id`, `meta`, `variables`, `premises`, `conclusions`, `assumptions`, `exceptions`, `deletions`, `guards`, `weight`, `roles`); other keys, such as a misspelt `assumption:`, are silently ignored by Carneades;
* every statement must be a term Carneades' parser accepts (`name`, `name(A,B)`, `¬name(A)` or a bare schema variable); a statement that does not parse is silently dropped when a scheme is instantiated;
* every variable used must be declared in `variables`, because `InstantiateScheme` binds parameters to the declared variables by position (never remove or reorder variables of a published scheme);
* every predicate needs a language template keyed `name/arity` (`name/0` for 0-ary predicates, which is how Carneades looks them up); the template is filled with Go's `fmt.Sprintf`, so the number of `%s` verbs must match the arity and each argument must be printed exactly once;
* the category files must agree exactly with `walton.yml`, every scheme must be in exactly one category file, and
* regression tests pin the direction of the schemes whose logic was once wrong (see `CHANGELOG.md`).

A second, independent check loads every file with the Carneades 4 engine itself (its YAML importer, its `validation` package, scheme instantiation and the GoCHR rule translation). It is not part of this repository because it needs a Go toolchain and the engine sources; `PLAN.md` describes how it was run and what it still reports.

## Known limitations

* Five schemes (`ad_hominem`, `practical_necessary_condition`, `practical_sufficient_condition`, `regulative_rule`, `sorites_slippery_slope`) have a variable that occurs only in a conclusion, assumption or exception, as in the book; Carneades' own validator reports these as problems because its inference engine needs range-restricted rules. The validator here reports them as warnings (`RANGE_RESTRICTION`).
* Misspelt identifiers are kept so that existing argument graphs keep working: scheme ids such as `exeption_to_rule`, `epistemic_ignorence`, `exeptional`, predicate names such as `recieves_evaluation`, `oficcial_rulebook`, `succesful_account`, the predicate `true/1` (which Carneades' validator rejects as a boolean), and the file name `5_casual-reasoning.yml`. See `PLAN.md`.
* Some schemes use 0-ary statements (for example `background`, `being_credible`) where the book's wording has no obvious variables.
* Negated statements (`¬presents(X,P)`) are printed by Carneades as the raw term; the engine does not apply the language inside a negation.

#### Updates
##### 2019-10-08

According to our correspondence with **Dr. Douglas Walton** on September 19, 2019, in which he informed us about the changes he made on some of the argumentation schemes which were presented in [**Argumentation Schemes (2008)**](https://www.cambridge.org/core/books/argumentation-schemes/9AE7E4E6ABDE690565442B2BD516A8B6) , we implemented these changes in our file:

* _Argument From Precedent_ was changed to _Argument From Exception To A Rule_.
* Spelling error was corrected in _Abductive Argumentation Scheme_.
* Spelling error was corrected in _Argument From Evidence to Hypothesis_.

We wish to thank **Dr. Douglas Walton** for his comments and corrections on _Carneades YAML (CYML)_ files at this repository.
