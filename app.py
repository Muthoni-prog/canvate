"""Glass Jury - Streamlit front end.
Every verdict, score and reason comes from MeTTa (rules.metta / data.metta) via run.py.
Streamlit only draws the screen and passes juror changes (weights, gates, threshold) to MeTTa."""
import os
import re
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

import run  # noqa: E402  (loads rules.metta + data.metta into MeTTa)

CRITERIA = ["theme-fit", "message", "provenance", "originality"]
GATES = {
    "consent": "Artist consent on record",
    "ai-disclosure": "AI use disclosed",
    "rights": "Rights holder known",
}
ICON = {"selected": "🟢", "needs-review": "🟠", "not-selected": "⚪"}
LABEL = {"selected": "Selected", "needs-review": "Needs human review", "not-selected": "Not selected"}


def read_defaults():
    """Default jury settings, read from rules.metta (the source of truth)."""
    text = (HERE / "rules.metta").read_text(encoding="utf-8")
    weights = {c: int(m) for c, m in re.findall(r"^\(weight ([\w-]+) (\d+)\)", text, re.M)}
    threshold = int(re.search(r"^\(threshold select (\d+)\)", text, re.M).group(1))
    return weights, threshold


DEFAULT_W, DEFAULT_T = read_defaults()


def set_threshold(new):
    old = int(run.one("(match &self (threshold select $t) $t)"))
    run.metta.run(f"!(remove-atom &self (threshold select {old}))")
    run.metta.run(f"!(add-atom &self (threshold select {new}))")


def apply_settings(weights, threshold, gates_on):
    for c, w in weights.items():
        if run.get_weight(c) != w:
            run.set_weight(c, w)
    set_threshold(threshold)
    for g, on in gates_on.items():
        run.toggle_gate(g, False)  # remove first so we never add duplicates
        if on:
            run.toggle_gate(g, True)


# ---------------------------------------------------------------- page
st.set_page_config(page_title="Glass Jury", page_icon="🔍", layout="wide")
st.title("🔍 Glass Jury")
st.caption(
    "A glass-box jury assistant. Every decision is a MeTTa rule you can inspect and challenge. "
    "Synthetic sample data only."
)

# ---- sidebar: the juror challenge controls
with st.sidebar:
    st.header("Juror challenge")
    st.write("Change the rules and watch the verdicts move.")
    weights = {
        c: st.slider(f"Weight: {c}", 0, 6, DEFAULT_W.get(c, 2), key=f"w_{c}")
        for c in CRITERIA
    }
    threshold = st.slider("Score needed to be selected", 5, 40, DEFAULT_T, key="thr")
    st.subheader("Hard gates")
    st.caption("A failed gate sends the work to a human. It is never auto-rejected.")
    gates_on = {g: st.checkbox(label, value=True, key=f"g_{g}") for g, label in GATES.items()}
    if st.button("Reset to default rules"):
        for c in CRITERIA:
            st.session_state[f"w_{c}"] = DEFAULT_W.get(c, 2)
        st.session_state["thr"] = DEFAULT_T
        for g in GATES:
            st.session_state[f"g_{g}"] = True
        st.rerun()

# ---- baseline (default rules), then the juror's rules
apply_settings(DEFAULT_W, DEFAULT_T, {g: True for g in GATES})
before = run.evaluate_all()
apply_settings(weights, threshold, gates_on)
after = run.evaluate_all()
b = {r["id"]: r for r in before}

# ---- summary tiles
counts = {v: sum(1 for r in after if r["verdict"] == v) for v in ICON}
c1, c2, c3 = st.columns(3)
c1.metric("Selected", counts["selected"])
c2.metric("Needs human review", counts["needs-review"])
c3.metric("Not selected", counts["not-selected"])

# ---- what changed
st.subheader("What changed")
moved = [r for r in after if r["verdict"] != b[r["id"]]["verdict"]]
rescored = [r for r in after if r["verdict"] == b[r["id"]]["verdict"] and r["score"] != b[r["id"]]["score"]]
if not moved and not rescored:
    st.info("Rules match the defaults. Change a weight, the threshold or a gate in the sidebar.")
else:
    for r in moved:
        o = b[r["id"]]
        st.success(
            f"**{r['title']}**: {LABEL[o['verdict']]} ({o['score']}) → "
            f"**{LABEL[r['verdict']]}** ({r['score']})"
        )
    if rescored:
        with st.expander(f"{len(rescored)} more changed score but kept the same verdict"):
            for r in rescored:
                o = b[r["id"]]
                st.write(f"{r['title']}: {o['score']} → {r['score']} ({LABEL[r['verdict']]})")

# ---- results table
st.subheader("Results")
st.dataframe(
    [
        {
            "": ICON[r["verdict"]],
            "Artwork": r["title"],
            "Verdict": LABEL[r["verdict"]],
            "Score": r["score"],
            "Confidence": r["confidence"],
            "Flags": ", ".join(
                [f"gate: {g}" for g in r["gates"]]
                + [f"gap: {c}" for c in r["missing"]]
                + [f"weak: {c}" for c in r["weak"]]
            ) or "-",
        }
        for r in after
    ],
    hide_index=True,
    width="stretch",
)

# ---- the glass box: why?
st.subheader("Why? (the glass box)")
for r in after:
    with st.expander(f"{ICON[r['verdict']]} {r['title']}: {LABEL[r['verdict']]} (score {r['score']})"):
        for g in r["gates"]:
            st.error(f"Gate failed: {run.reason(g)}. Sent to human review.")
        rows = []
        for c in CRITERIA:
            pts = r["breakdown"].get(c, "no data")
            rows.append({"Criterion": c, "Weight": str(weights[c]), "Points": str(pts)})
        st.table(rows)
        for c in r["missing"]:
            st.warning(f"Gap: no data for '{c}'. It was not guessed, so confidence is reduced.")
        for c in r["weak"]:
            st.info(f"Weak spot: '{c}' is rated low.")
        st.caption(
            f"Selected if score ≥ {threshold} and no gate fails. Confidence: {r['confidence']}."
        )

st.divider()
st.caption(
    "Limits: scoring is simple (weight × a three-level rating) and the data is synthetic. "
    "Next step: real data, shared with consent."
)