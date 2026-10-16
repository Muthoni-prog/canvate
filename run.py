"""Glass Jury runner. Python only loads files, calls MeTTa, and prints.
All decisions and reasoning come from rules.metta / data.metta."""
from hyperon import MeTTa

metta = MeTTa()
metta.run(open("rules.metta", encoding="utf-8").read())
metta.run(open("data.metta", encoding="utf-8").read())


def q(expr):
    """Run a MeTTa query, return list of result strings."""
    res = metta.run(f"!{expr}")
    return [str(a) for a in res[0]] if res else []


def one(expr):
    r = q(expr)
    return r[0] if r else None


def collect(expr):
    r = metta.run(f"!(collapse {expr})")
    if not r or not r[0]:
        return []
    return [str(a) for a in r[0][0].get_children()]


def reason(gate):
    return (one(f"(match &self (reason {gate} $r) $r)") or gate).strip('"')


def artworks():
    ids = q("(match &self (artwork $a) $a)")
    return sorted(ids)


def evaluate(a):
    return {
        "id": a,
        "title": (one(f"(match &self (title {a} $t) $t)") or a).strip('"'),
        "verdict": one(f"(verdict {a})"),
        "score": int(one(f"(score {a})")),
        "gates": collect(f"(gate-fail {a} $g)"),
        "breakdown": {c: (one(f"(crit {a} {c})") or "no data")
                      for c in q("(match &self (criterion $c) $c)")},
        "missing": collect(f"(missing {a})"),
        "weak": collect(f"(weak {a})"),
        "confidence": one(f"(confidence {a})"),
    }


def evaluate_all():
    rows = [evaluate(a) for a in artworks()]
    return sorted(rows, key=lambda r: (-r["score"], r["id"]))


def explain(r):
    print(f"\n[{r['id']}] {r['title']}  ->  {r['verdict'].upper()}  "
          f"(score {r['score']}, confidence {r['confidence']})")
    for g in r["gates"]:
        print(f"   GATE FAILED: {reason(g)}  -> sent to human review")
    for c, pts in r["breakdown"].items():
        print(f"   {c}: {pts} points" if pts != "no data" else f"   {c}: no data")
    for c in r["missing"]:
        print(f"   GAP: no data for '{c}' (not guessed)")
    for c in r["weak"]:
        print(f"   WEAK: '{c}' rated low")


def show_all(title):
    print("\n" + "=" * 60 + f"\n{title}\n" + "=" * 60)
    rows = evaluate_all()
    for r in rows:
        explain(r)
    return rows


# ---- The challenge loop ----
def get_weight(c):
    return int(one(f"(match &self (weight {c} $w) $w)"))


def set_weight(c, new):
    old = get_weight(c)
    metta.run(f"!(remove-atom &self (weight {c} {old}))")
    metta.run(f"!(add-atom &self (weight {c} {new}))")


def toggle_gate(g, on):
    if on:
        metta.run(f"!(add-atom &self (active-gate {g}))")
    else:
        metta.run(f"!(remove-atom &self (active-gate {g}))")


def diff(before, after):
    print("\n--- WHAT CHANGED ---")
    b = {r["id"]: r for r in before}
    changed = False
    for r in after:
        o = b[r["id"]]
        if o["verdict"] != r["verdict"] or o["score"] != r["score"]:
            changed = True
            print(f"{r['id']} {r['title']}: {o['verdict']} ({o['score']}) -> "
                  f"{r['verdict']} ({r['score']})")
    if not changed:
        print("No change.")


if __name__ == "__main__":
    before = show_all("ROUND 1: default jury rules")

    print("\n\n>>> A juror challenges: 'Originality should matter more.'")
    old = get_weight("originality")
    set_weight("originality", 4)
    print(f">>> weight(originality): {old} -> 4")
    after = show_all("ROUND 2: after the challenge")
    diff(before, after)

    set_weight("originality", old)  # restore