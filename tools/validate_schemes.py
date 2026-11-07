#!/usr/bin/env python3
"""Validate the Walton argumentation-scheme YAML files for Carneades 4.

Usage:  python3 tools/validate_schemes.py [repo_root] [--json]
Exit status 0 if there are no ERRORs (WARNINGs are reported but allowed).

Checks follow Carneades 4 semantics (github.com/carneades/carneades-4):
  * every file parses as YAML and has an 'argument_schemes' list;
  * every scheme has a unique id, only keys Carneades understands, list-valued
    premises/conclusions/assumptions/exceptions/variables, and at least one premise
    and one conclusion;
  * every statement is a well-formed predicate: [¬]name or [¬]name(arg, ...);
  * every variable used is declared, and every declared variable is used;
  * every predicate used has a language template keyed name/arity (0-ary predicates
    need name/0, which is how Carneades looks them up), with exactly as many %s/%v
    verbs as the arity (Carneades fills templates with Go's Sprintf);
  * the category files agree exactly with walton.yml, every scheme in walton.yml is
    in exactly one category file, and every category scheme is in walton.yml;
  * regression tests pin the direction of schemes whose logic was once wrong.
Requires PyYAML.
"""
import sys, os, re, glob, json

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

ALLOWED_KEYS = {"id", "meta", "variables", "premises", "conclusions", "assumptions",
                "exceptions", "weight", "roles", "deletions", "guards"}
LIST_FIELDS = ("premises", "conclusions", "assumptions", "exceptions")

# ------------------------------------------------------------------ strict term grammar
TOK = re.compile(r"\s*(?:(¬)|([a-z][A-Za-z0-9_]*)|([A-Z_][A-Za-z0-9_]*)|(-?\d+(?:\.\d+)?)|([(),]))")

class TermError(ValueError):
    pass

def parse_statement(s):
    """Return (negated, functor, arity, variables) or raise TermError."""
    toks, pos = [], 0
    s = s.strip()
    while pos < len(s):
        m = TOK.match(s, pos)
        if not m or m.end() == pos:
            raise TermError(f"unexpected character {s[pos]!r} at position {pos}")
        toks.append(m.groups()); pos = m.end()
    i = 0
    neg = False
    if i < len(toks) and toks[i][0]:
        neg = True; i += 1
    def term(i):
        if i >= len(toks): raise TermError("unexpected end of statement")
        neg_, atom, var, num, punct = toks[i]
        if neg_:                                   # ¬ may negate an argument, e.g. opposite_action(A,S,¬X)
            t, j = term(i + 1)
            return ("neg", "¬", [t]), j
        if var: return ("var", var, []), i + 1
        if num: return ("num", num, []), i + 1
        if atom:
            if i + 1 < len(toks) and toks[i + 1][4] == "(":
                args, j = [], i + 2
                while True:
                    a, j = term(j); args.append(a)
                    if j < len(toks) and toks[j][4] == ",": j += 1; continue
                    if j < len(toks) and toks[j][4] == ")": return ("cmp", atom, args), j + 1
                    raise TermError(f"expected ',' or ')' in arguments of {atom}")
            return ("atom", atom, []), i + 1
        raise TermError(f"unexpected token {[t for t in toks[i] if t][0]!r}")
    # A statement is a predicate, or a bare schema variable standing for a whole statement
    # (expert_opinion concludes S). A parenthesised variable such as (X) is rejected.
    if i >= len(toks) or not (toks[i][1] or toks[i][2]):
        raise TermError("statement must be a lower-case predicate or a schema variable")
    t, j = term(i)
    if j != len(toks):
        raise TermError("trailing tokens after the statement")
    vs = set()
    def walk(t):
        if t[0] == "var": vs.add(t[1])
        for a in t[2]: walk(a)
    walk(t)
    if t[0] == "var":
        return neg, None, 0, vs                    # schema variable: no functor, no template needed
    return neg, t[1], len(t[2]), vs

VERB = re.compile(r"%(?:%|(\[\d+\])?([sv])|.?)")

def template_args(tpl, arity):
    """Simulate how Go's Sprintf consumes arguments for templates using %s, %v and %[n]s.
    Return (malformed_verbs, problems): problems lists arguments out of range or never used."""
    bad, used, argnum = [], set(), 0
    for m in VERB.finditer(tpl):
        v = m.group(0)
        if v == "%%": continue
        if not m.group(2):
            bad.append(v); continue
        if m.group(1): argnum = int(m.group(1)[1:-1]) - 1
        used.add(argnum); argnum += 1
    probs = []
    over = sorted(i + 1 for i in used if i < 0 or i >= arity)
    if over: probs.append(f"refers to argument(s) {over} but the arity is {arity} (Go prints %!s(MISSING))")
    unused = sorted(i + 1 for i in set(range(arity)) - used)
    if unused: probs.append(f"never prints argument(s) {unused} of {arity}")
    return bad, probs

# ------------------------------------------------------------------ helpers
class Report:
    def __init__(self): self.items = []
    def add(self, sev, code, where, msg): self.items.append(dict(severity=sev, code=code, where=where, message=msg))
    def errors(self): return [x for x in self.items if x["severity"] == "ERROR"]

def raw_duplicate_keys(path, section):
    """YAML silently keeps the last of duplicate mapping keys; find them in the raw text."""
    seen, dups, inside = {}, [], False
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if re.match(rf"^{section}:\s*$", line): inside = True; continue
        if inside and re.match(r"^\S", line): break
        m = re.match(r"^  ([^\s#][^:]*?):\s", line) if inside else None
        if m:
            k = m.group(1).strip().strip("'\"")
            if k in seen: dups.append((k, seen[k], n))
            else: seen[k] = n
    return dups

def scheme_statements(x):
    for f in LIST_FIELDS:
        v = x.get(f)
        if isinstance(v, list):
            for s in v: yield f, s

def check_file(path, rel, rep):
    try:
        d = yaml.safe_load(open(path, encoding="utf-8"))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        loc = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        rep.add("ERROR", "YAML_PARSE", rel, f"{getattr(e, 'problem', str(e))}{loc}")
        return None
    if not isinstance(d, dict) or not isinstance(d.get("argument_schemes"), list):
        rep.add("ERROR", "NO_SCHEMES", rel, "missing top-level 'argument_schemes' list"); return None
    lang = d.get("language") or {}
    if not isinstance(lang, dict):
        rep.add("ERROR", "LANGUAGE_NOT_MAPPING", rel, "'language' must be a mapping"); lang = {}
    for k, a, b in raw_duplicate_keys(path, "language"):
        rep.add("ERROR", "LANGUAGE_DUPLICATE_KEY", rel, f"template {k!r} defined at lines {a} and {b}; YAML keeps only the last")
    for k, v in lang.items():
        if not re.fullmatch(r"¬?[a-z][A-Za-z0-9_]*/\d+", str(k)):
            rep.add("ERROR", "LANGUAGE_KEY_FORMAT", rel, f"key {k!r} is not name/arity; Carneades never finds it (0-ary predicates need name/0)")
            continue
        bad, probs = template_args(str(v), int(str(k).split("/")[1]))
        if bad: rep.add("ERROR", "TEMPLATE_BAD_VERB", rel, f"{k}: malformed format verb(s) {bad} in {v!r}")
        for p in probs: rep.add("ERROR", "TEMPLATE_ARITY", rel, f"{k}: template {p}: {v!r}")
    ids, used = {}, set()
    for i, x in enumerate(d["argument_schemes"]):
        where = f"{rel}#{i + 1}"
        if not isinstance(x, dict):
            rep.add("ERROR", "SCHEME_NOT_MAPPING", where, f"entry is {type(x).__name__}, not a mapping: {str(x)[:60]!r}"); continue
        sid = x.get("id")
        if not isinstance(sid, str) or not sid.strip():
            rep.add("ERROR", "ID_MISSING", where, "scheme has no id"); continue
        where = f"{rel}:{sid}"
        if sid in ids: rep.add("ERROR", "ID_DUPLICATE", where, f"id also used by entry {ids[sid] + 1}; Carneades keeps only the last")
        ids[sid] = i
        for k in x:
            if k not in ALLOWED_KEYS: rep.add("ERROR", "UNKNOWN_KEY", where, f"key {k!r} is not read by Carneades (did you mean 'assumptions'?)" if k == "assumption" else f"key {k!r} is not read by Carneades")
        meta = x.get("meta")
        if not isinstance(meta, dict) or not meta.get("title"): rep.add("WARNING", "META_TITLE_MISSING", where, "no meta.title")
        elif not str(meta.get("source") or "").strip(): rep.add("WARNING", "META_SOURCE_MISSING", where, "no meta.source")
        for f in LIST_FIELDS + ("variables",):
            if f in x and x[f] is not None and not isinstance(x[f], list):
                rep.add("ERROR", "FIELD_NOT_LIST", where, f"{f!r} is a {type(x[f]).__name__} ({str(x[f])[:50]!r}), not a list")
        if not (isinstance(x.get("premises"), list) and x["premises"]): rep.add("ERROR", "NO_PREMISES", where, "scheme has no premises")
        if not (isinstance(x.get("conclusions"), list) and x["conclusions"]): rep.add("ERROR", "NO_CONCLUSIONS", where, "scheme has no conclusions")
        declared = set(x.get("variables") or []) if isinstance(x.get("variables"), list) else set()
        allvars, premvars = set(), set()
        for f, s in scheme_statements(x):
            try:
                neg, fn, ar, vs = parse_statement(str(s))
            except TermError as e:
                rep.add("ERROR", "STATEMENT_SYNTAX", where, f"{f}: {s!r}: {e}"); continue
            allvars |= vs
            if f == "premises": premvars |= vs
            if fn is None: continue                      # schema variable
            key = f"{fn}/{ar}"; used.add(key)
            if key not in lang:
                rep.add("ERROR", "TEMPLATE_MISSING", where, f"{f}: {s!r} needs language template {key!r} in this file")
        for v in sorted(allvars - declared): rep.add("ERROR", "VARIABLE_UNDECLARED", where, f"variable {v} is used but not declared in 'variables'")
        for v in sorted(declared - allvars): rep.add("WARNING", "VARIABLE_UNUSED", where, f"variable {v} is declared but never used")
        unbound = sorted((allvars & declared) - premvars)
        if unbound: rep.add("WARNING", "RANGE_RESTRICTION", where, f"variable(s) {unbound} occur only outside the premises; they are bound only when the scheme is instantiated with parameters")
    for k in sorted(set(lang) - used):
        rep.add("WARNING", "TEMPLATE_UNUSED", rel, f"template {k!r} is not used by any scheme in this file")
    return d

# ------------------------------------------------------------------ regression tests (direction of corrected schemes)
# Each entry pins a scheme whose logic once contradicted its source, so the error cannot return.
# "WRM 2008" is Walton, Reed & Macagno, Argumentation Schemes, Cambridge University Press, 2008.
def regression(master, rep):
    S = {x["id"]: x for x in master["argument_schemes"] if isinstance(x, dict)}
    def fns(x, f):
        out = []
        for s in x.get(f) or []:
            try: out.append(parse_statement(str(s))[1])
            except TermError: out.append(None)
        return out
    def args(s):
        m = re.search(r"\((.*)\)", str(s)); return [a.strip() for a in m.group(1).split(",")] if m else []
    def stmt(x, f, name):
        return next((s for s in x.get(f) or [] if str(s).lstrip("¬").startswith(name + "(")), None)
    checks = [
        ("division_generic", lambda x: fns(x, "premises") == ["has_property"] and fns(x, "conclusions") == ["all_parts_propert"]
            and fns(x, "assumptions") == ["divisionally_hereditary"], "division runs whole -> parts and asks whether the property passes to the parts (WRM 2008, sec. 10.1, p. 317)"),
        ("composition_generic", lambda x: fns(x, "premises") == ["all_parts_propert"] and fns(x, "conclusions") == ["has_property"]
            and fns(x, "assumptions") == ["compositionally_hereditary"], "composition runs parts -> whole and asks whether the whole inherits the property (sec. 9.1, p. 316)"),
        ("evidence_hypothesis_falsification", lambda x: [str(c).replace(" ", "") for c in x["conclusions"]] == ["¬H"],
            "falsification concludes that the hypothesis H is false (sec. 32.2, pp. 331-332)"),
        ("from_example", lambda x: fns(x, "premises") == ["has_properties"] and fns(x, "conclusions") == ["both_properties"],
            "argument from example runs from the particular case to the generalization (sec. 6.1, p. 314)"),
        ("common_folk_ad_populum", lambda x: x["premises"] == ["background"] and x["conclusions"] == ["being_credible"],
            "the speaker's ordinariness is the premise and greater credibility the conclusion (sec. 4.10, p. 313)"),
        ("moral_justification_ad_populum_excuse", lambda x: fns(x, "conclusions") == ["morally_acceptable_action"],
            "the conclusion is that the speaker's action is morally justified (sec. 4.6, p. 312)"),
        ("danger", lambda x: stmt(x, "premises", "occur") and args(x["conclusions"][0]) == args(stmt(x, "premises", "occur"))[:1],
            "the conclusion is not to bring about the action, not the danger (sec. 37, p. 334)"),
        ("treat", lambda x: "position_to_bring_about" in fns(x, "premises") and len(args(stmt(x, "premises", "cited_bad_consequences") or "")) == 2,
            "the proponent is in a position to bring about the cited consequence (sec. 35, p. 333)"),
        ("abductive_backward", lambda x: "succesful_account" in fns(x, "premises"),
            "the chosen account must explain the data most successfully (sec. 31.1, pp. 329-330)"),
        ("opposition-normative", lambda x: "cannot_opposite_evaluation" in fns(x, "premises")
            and args(stmt(x, "premises", "recieves_evaluation"))[1:] == args(stmt(x, "premises", "cannot_opposite_evaluation"))[1:2],
            "the minor premise instantiates the major premise's antecedent (sec. 11.2, p. 318)"),
        ("sacrifice", lambda x: args(stmt(x, "premises", "great_sacrifice"))[2:] == args(x["conclusions"][0])[1:],
            "the value in the conditional premise is the value concluded (sec. 20, p. 322)"),
    ]
    for sid, cond, msg in checks:
        if sid not in S:
            rep.add("ERROR", "REGRESSION", f"walton.yml:{sid}", "scheme missing"); continue
        try: ok = bool(cond(S[sid]))
        except Exception: ok = False
        if not ok: rep.add("ERROR", "REGRESSION", f"walton.yml:{sid}", msg)

def cross_files(root, master, cats, rep):
    M = {x["id"]: x for x in master["argument_schemes"] if isinstance(x, dict)}
    ML = master.get("language") or {}
    home = {}
    for rel, d in cats.items():
        for x in d["argument_schemes"]:
            if not isinstance(x, dict) or "id" not in x: continue
            home.setdefault(x["id"], []).append(rel)
            if x["id"] not in M:
                rep.add("ERROR", "MISSING_FROM_WALTON_YML", f"{rel}:{x['id']}", "scheme is in a category file but not in walton.yml")
            elif x != M[x["id"]]:
                diff = sorted(k for k in set(x) | set(M[x["id"]]) if x.get(k) != M[x["id"]].get(k))
                rep.add("ERROR", "DIFFERS_FROM_WALTON_YML", f"{rel}:{x['id']}", f"field(s) {diff} differ from walton.yml")
        for k, v in (d.get("language") or {}).items():
            if k in ML and ML[k] != v:
                rep.add("ERROR", "TEMPLATE_DIFFERS_FROM_WALTON_YML", rel, f"{k}: {v!r} vs walton.yml {ML[k]!r}")
    for sid in M:
        if sid not in home: rep.add("ERROR", "UNCATEGORIZED", f"walton.yml:{sid}", "scheme is in no category file")
    for sid, files in home.items():
        if len(set(files)) > 1: rep.add("ERROR", "MULTIPLE_CATEGORIES", sid, f"scheme appears in {sorted(set(files))}")

def main(argv):
    root = next((a for a in argv[1:] if not a.startswith("--")), os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rep = Report()
    master = check_file(os.path.join(root, "walton.yml"), "walton.yml", rep)
    cats = {}
    for p in sorted(glob.glob(os.path.join(root, "[A-Z]_*", "*.yml"))):
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        d = check_file(p, rel, rep)
        if d is not None: cats[rel] = d
    if master is not None:
        regression(master, rep)
        cross_files(root, master, cats, rep)
    if "--json" in argv:
        print(json.dumps(rep.items, indent=1, ensure_ascii=False))
    else:
        for it in rep.items:
            print(f"{it['severity']:7} {it['code']:32} {it['where']}: {it['message']}")
        e, w = len(rep.errors()), len(rep.items) - len(rep.errors())
        print(f"\n{e} error(s), {w} warning(s) in {1 + len(cats)} file(s).")
    return 1 if rep.errors() else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
