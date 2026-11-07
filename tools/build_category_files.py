#!/usr/bin/env python3
"""Generate the category files (A_reasoning/..., B_..., C_...) from walton.yml.

Usage:  python3 tools/build_category_files.py [repo_root]           write the files
        python3 tools/build_category_files.py [repo_root] --check   exit 1 if any file is stale

walton.yml is the only hand-edited scheme file. categories.yml says which schemes
go into which category file. Each generated file contains, verbatim from
walton.yml, the language templates its schemes use and the scheme blocks
themselves, so a category file can be loaded into Carneades 4 on its own.
Requires PyYAML.
"""
import sys, os, re, json
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_schemes import parse_statement, LIST_FIELDS, TermError  # noqa: E402

HEADER = ("# Generated from walton.yml by tools/build_category_files.py. Do not edit:\n"
          "# change walton.yml (or the grouping in categories.yml) and run the tool again.\n")
SOURCE = ("Walton, Douglas and Reed, Chris and Macagno, Fabrizio (2008). "
          "Argumentation Schemes. Cambridge University Press.")


def read_master(path):
    """Return (template lines keyed by name/arity, scheme blocks keyed by id), both verbatim."""
    lines = open(path, encoding="utf-8").read().split("\n")
    lang_start = next(i for i, l in enumerate(lines) if re.match(r"^language:\s*$", l))
    schemes_start = next(i for i, l in enumerate(lines) if re.match(r"^argument_schemes:\s*$", l))
    templates = {}
    for l in lines[lang_start + 1:schemes_start]:
        m = re.match(r"^  ([^\s#][^:]*?):\s", l)
        if m:
            templates[m.group(1).strip().strip("'\"")] = l.rstrip()
    starts = [i for i in range(schemes_start + 1, len(lines)) if re.match(r"^  - id:\s*\S", lines[i])]
    blocks = {}
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        sid = re.match(r"^  - id:\s*(\S+)", lines[i]).group(1)
        if sid in blocks:
            raise SystemExit(f"walton.yml: scheme id {sid!r} occurs more than once")
        block = list(lines[i:end])          # verbatim: folded scalars keep their trailing spaces
        while block and not block[-1].strip():
            block.pop()
        blocks[sid] = "\n".join(block)
    return templates, blocks


def templates_used(block):
    """name/arity keys of every predicate in the scheme block (schema variables need none)."""
    scheme = yaml.safe_load("argument_schemes:\n" + block)["argument_schemes"][0]
    keys = []
    for field in LIST_FIELDS:
        for st in scheme.get(field) or []:
            try:
                _, functor, arity, _ = parse_statement(str(st))
            except TermError as e:
                raise SystemExit(f"{scheme['id']}: cannot parse statement {st!r}: {e}")
            if functor is not None:
                keys.append(f"{functor}/{arity}")
    return keys


def render(title, templates, blocks, ids):
    used = []
    for sid in ids:
        for k in templates_used(blocks[sid]):
            if k not in used:
                used.append(k)
    missing = [k for k in used if k not in templates]
    if missing:
        raise SystemExit(f"{title}: walton.yml has no template for {missing}")
    out = [HEADER, "meta:", f"  title: {json.dumps(title, ensure_ascii=False)}",
           f"  source: {json.dumps(SOURCE)}", "language:"]
    out += [templates[k] for k in templates if k in used]      # walton.yml order
    out += ["", "argument_schemes:"]
    out += [blocks[sid] + "\n" for sid in ids]
    return "\n".join(out)


def main(argv):
    root = next((a for a in argv[1:] if not a.startswith("--")), os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    check = "--check" in argv
    templates, blocks = read_master(os.path.join(root, "walton.yml"))
    cats = yaml.safe_load(open(os.path.join(root, "categories.yml"), encoding="utf-8"))
    seen = {}
    for rel, spec in cats.items():
        for sid in spec["schemes"]:
            if sid not in blocks:
                raise SystemExit(f"categories.yml: {rel} lists {sid!r}, which is not in walton.yml")
            if sid in seen:
                raise SystemExit(f"categories.yml: {sid!r} is listed in both {seen[sid]} and {rel}")
            seen[sid] = rel
    unassigned = [sid for sid in blocks if sid not in seen]
    if unassigned:
        raise SystemExit(f"categories.yml does not place these schemes of walton.yml: {unassigned}")
    stale = []
    for rel, spec in cats.items():
        text = render(spec["title"], templates, blocks, spec["schemes"])
        path = os.path.join(root, rel)
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if current == text:
            continue
        if check:
            stale.append(rel)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8", newline="\n").write(text)
            print("wrote", rel)
    if stale:
        print("stale (run tools/build_category_files.py):", *stale, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
