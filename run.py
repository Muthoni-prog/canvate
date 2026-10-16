"""Glass Jury runner.

Python only loads files, asks MeTTa questions, and prints what MeTTa answers.
Every decision and every reason comes from rules.metta / data.metta
(see the `(why $artwork)` rule, which returns the whole reasoning trail).

Usage:  python run.py
"""
import csv
import io
import re
from pathlib import Path

from hyperon import MeTTa

HERE = Path(__file__).resolve().parent
RULES_TEXT = (HERE / "rules.metta").read_text(encoding="utf-8")
DEMO_DATA = (HERE / "data.metta").read_text(encoding="utf-8")


def _clean(s):
    """MeTTa string atoms print with quotes; drop them for display."""
    return s.strip('"')


class Jury:
    """One independent MeTTa jury (own rules, own data, own settings)."""

    def __init__(self, data_text=None):
        self.metta = MeTTa()
        self.metta.run(RULES_TEXT)
        self.metta.run(DEMO_DATA if data_text is None else data_text)

    # ---- low-level MeTTa access ------------------------------------
    def q(self, expr):
        res = self.metta.run(f"!{expr}")
        return [str(a) for a in res[0]] if res else []

    def one(self, expr):
        r = self.q(expr)
        return r[0] if r else None

    def atoms(self, expr):
        """Run (collapse expr); return the result atoms as a list."""
        r = self.metta.run(f"!(collapse {expr})")
        if not r or not r[0]:
            return []
        return list(r[0][0].get_children())

    @staticmethod
    def parts(atom):
        """('gate', 'consent', 'no-record', 'text') from a MeTTa expression atom."""
        return tuple(_clean(str(x)) for x in atom.get_children())

    # ---- settings (stored in MeTTa as atoms) -------------------------
    def criteria(self):
        return self.q("(match &self (criterion $c) $c)")

    def artworks(self):
        return sorted(self.q("(match &self (artwork $a) $a)"),
                      key=lambda s: (len(s), s))

    def get_weight(self, c):
        return int(self.one(f"(match &self (weight {c} $w) $w)"))

    def set_weight(self, c, new):
        old = self.get_weight(c)
        if old != new:
            self.metta.run(f"!(remove-atom &self (weight {c} {old}))")
            self.metta.run(f"!(add-atom &self (weight {c} {new}))")

    def get_threshold(self):
        return int(self.one("(match &self (threshold select $t) $t)"))

    def set_threshold(self, new):
        old = self.get_threshold()
        if old != new:
            self.metta.run(f"!(remove-atom &self (threshold select {old}))")
            self.metta.run(f"!(add-atom &self (threshold select {new}))")

    def active_gates(self):
        return set(self.q("(match &self (active-gate $g) $g)"))

    def toggle_gate(self, g, on):
        if on and g not in self.active_gates():
            self.metta.run(f"!(add-atom &self (active-gate {g}))")
        elif not on and g in self.active_gates():
            self.metta.run(f"!(remove-atom &self (active-gate {g}))")

    def settings(self):
        return {
            "weights": {c: self.get_weight(c) for c in self.criteria()},
            "threshold": self.get_threshold(),
            "gates": self.active_gates(),
        }

    # ---- evaluation: all reasoning is MeTTa's, we only parse ----------
    def evaluate(self, a):
        atoms = self.atoms(f"(why {a})")
        row = {
            "id": a,
            "title": _clean(self.one(f"(match &self (title {a} $t) $t)") or a),
            "verdict": None, "outcome_text": "", "score": 0, "threshold": None,
            "confidence": None, "gates": [], "missing": [], "weak": [],
            "breakdown": {c: "no data" for c in self.criteria()},
            "trace": [str(x) for x in atoms],  # raw MeTTa atoms, for display
        }
        for at in atoms:
            p = self.parts(at)
            kind = p[0]
            if kind == "gate":
                row["gates"].append({"gate": p[1], "state": p[2], "reason": p[3]})
            elif kind == "points":
                row["breakdown"][p[1]] = int(p[2])
            elif kind == "gap":
                row["missing"].append(p[1])
            elif kind == "weak-spot":
                row["weak"].append(p[1])
            elif kind == "total":
                row["score"] = int(p[1])
            elif kind == "threshold":
                row["threshold"] = int(p[1])
            elif kind == "conf":
                row["confidence"] = p[1]
            elif kind == "outcome":
                row["verdict"], row["outcome_text"] = p[1], p[2]
        return row

    def evaluate_all(self):
        rows = [self.evaluate(a) for a in self.artworks()]
        return sorted(rows, key=lambda r: (-r["score"], r["id"]))


# ---- CSV upload: Python only converts rows into MeTTa facts -------------
CSV_COLUMNS = ["id", "title", "ai_used", "ai_disclosed", "consent", "rights",
               "theme_fit", "message", "provenance", "originality"]
_FACTS = {  # csv column -> (MeTTa predicate, allowed values)
    "ai_used": ("ai-used", {"yes", "no"}),
    "ai_disclosed": ("ai-disclosed", {"yes", "no", "na"}),
    "consent": ("consent", {"granted", "missing"}),
    "rights": ("rights", {"known", "unknown"}),
    "theme_fit": ("theme-fit", {"high", "medium", "low"}),
    "message": ("message", {"high", "medium", "low"}),
    "provenance": ("provenance", {"high", "medium", "low"}),
    "originality": ("originality", {"high", "medium", "low"}),
}
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
MAX_ROWS = 200


def csv_to_metta(text):
    """Turn CSV text into MeTTa facts. A blank cell becomes NO fact (a gap,
    never a guess). Only whitelisted values are accepted.
    Returns (metta_text, n_artworks, errors)."""
    errors, lines, seen = [], [], set()
    reader = csv.DictReader(io.StringIO(text))
    cols = [c.strip().lower() for c in (reader.fieldnames or [])]
    if "id" not in cols or "title" not in cols:
        return "", 0, ["The CSV needs at least the columns: id, title."]
    reader.fieldnames = cols
    for n, row in enumerate(reader, start=2):
        if len(seen) >= MAX_ROWS:
            errors.append(f"Only the first {MAX_ROWS} rows are used.")
            break
        raw_id = (row.get("id") or "").strip()
        if not _ID.match(raw_id):
            errors.append(f"Row {n}: id '{raw_id}' must start with a letter and use only "
                          "letters, numbers, - or _ (max 32).")
            continue
        aid = "w-" + raw_id.lower()
        if aid in seen:
            errors.append(f"Row {n}: duplicate id '{raw_id}'.")
            continue
        title = re.sub(r'["()\\;\r\n]', " ", row.get("title") or "").strip()[:80] or raw_id
        facts = [f"(artwork {aid})", f'(title {aid} "{title}")']
        for col, (pred, allowed) in _FACTS.items():
            val = (row.get(col) or "").strip().lower()
            if not val:
                continue  # blank = no fact = a gap
            if val not in allowed:
                errors.append(f"Row {n}: {col} '{val}' is not one of {sorted(allowed)}; "
                              "left blank.")
                continue
            facts.append(f"({pred} {aid} {val})")
        seen.add(aid)
        lines.append(" ".join(facts))
    return "\n".join(lines), len(seen), errors


# ---- printing (the command-line demo) ---------------------------------
def explain(r):
    print(f"\n[{r['id']}] {r['title']}  ->  {r['verdict'].upper()}  "
          f"(score {r['score']}, confidence {r['confidence']})")
    for g in r["gates"]:
        tag = "GATE FAILED" if g["state"] == "failed" else "GATE UNVERIFIED"
        print(f"   {tag}: {g['reason']}  -> sent to human review")
    for c, pts in r["breakdown"].items():
        print(f"   {c}: {pts} points" if pts != "no data" else f"   {c}: no data")
    for c in r["missing"]:
        print(f"   GAP: no data for '{c}' (not guessed)")
    for c in r["weak"]:
        print(f"   WEAK: '{c}' rated low")
    print(f"   WHY: {r['outcome_text']}")


def show_all(jury, title):
    print("\n" + "=" * 60 + f"\n{title}\n" + "=" * 60)
    rows = jury.evaluate_all()
    for r in rows:
        explain(r)
    return rows


def diff(before, after):
    print("\n--- WHAT CHANGED ---")
    b = {r["id"]: r for r in before}
    changed = False
    for r in after:
        o = b[r["id"]]
        if o["verdict"] != r["verdict"] or o["score"] != r["score"]:
            changed = True
            print(f"{r['title']}: {o['verdict']} ({o['score']}) -> "
                  f"{r['verdict']} ({r['score']})")
    if not changed:
        print("No change.")


if __name__ == "__main__":
    jury = Jury()
    before = show_all(jury, "ROUND 1: default jury rules")

    print("\n\n>>> A juror challenges: 'Originality should matter more.'")
    old = jury.get_weight("originality")
    jury.set_weight("originality", 4)
    print(f">>> weight(originality): {old} -> 4")
    after = show_all(jury, "ROUND 2: after the challenge")
    diff(before, after)