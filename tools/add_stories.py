#!/usr/bin/env python3
"""Write "Você sabia?" stories into the question files.

  python3 tools/add_stories.py STORIES.json

STORIES.json maps a question file to its rows, by 1-based position:
  { "10_mundiais.json": { "1": [x, xs, xsrc?, new_t?], ... }, ... }

  x      the story (20-240 characters), shown after the answer
  xs     the words it adds, checked against the row's own src article
  xsrc   optional [lang, article, [terms]] when the story rests on another page
  new_t  optional replacement for the question text (a fact that aged)

The files are rewritten one row per block, in the layout they were written in.
"""
import io, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
QDIR = os.path.join(ROOT, "tools", "questions")
J = lambda v: json.dumps(v, ensure_ascii=False)


def row_text(q):
    head = [f'"t": {J(q["t"])}']
    if q.get("type"): head.append(f'"type": {J(q["type"])}')
    mid = []
    if q.get("choices"): mid.append(f'"choices": {J(q["choices"])}')
    mid.append(f'"a": {J(q["a"])}')
    tail = [f'"d": {J(q.get("d"))}', f'"art": {J(q.get("art"))}', f'"src": {J(q["src"])}']
    lines = ["    { " + ", ".join(head) + ",", "      " + ", ".join(mid) + ",", "      " + ", ".join(tail)]
    extra = [f'"{k}": {J(q[k])}' for k in ("x", "xs", "xsrc") if q.get(k)]
    if extra:
        lines[-1] += ","
        lines.append("      " + ", ".join(extra))
    lines[-1] += " }"
    return "\n".join(lines)


def write_cat(path, cat):
    badge = f'"flag": {J(cat["flag"])}' if cat.get("flag") else f'"emoji": {J(cat.get("emoji", "⚽"))}'
    out = ["{", f'  "id": {J(cat["id"])}, "name": {J(cat["name"])}, {badge},',
           f'  "tag": {J(cat["tag"])}, "col": {J(cat["col"])}, "diff": {J(cat["diff"])},', '  "qs": [']
    out.append(",\n".join(row_text(q) for q in cat["qs"]))
    out += ["  ]", "}", ""]
    io.open(path, "w", encoding="utf-8").write("\n".join(out))


def main():
    stories = json.load(io.open(sys.argv[1], encoding="utf-8"))
    n = 0
    for fname, rows in stories.items():
        path = os.path.join(QDIR, fname)
        cat = json.load(io.open(path, encoding="utf-8"))
        for k, v in rows.items():
            q = cat["qs"][int(k) - 1]
            q["x"] = v[0]
            q["xs"] = v[1] if len(v) > 1 else []
            if len(v) > 2 and v[2]: q["xsrc"] = v[2]
            if len(v) > 3 and v[3]: q["t"] = v[3]
            if not q["xs"]: q.pop("xs")
            n += 1
        write_cat(path, cat)
    print(f"{n} stories written into {len(stories)} files")


main()
