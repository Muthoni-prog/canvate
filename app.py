"""Glass Jury - Streamlit front end.

Every verdict, score and reason comes from MeTTa (rules.metta / data.metta),
including the full reasoning trail from the `(why $artwork)` rule.
Streamlit only draws the screen and passes juror changes (weights, gates,
threshold) to MeTTa as atoms. Each browser session gets its own MeTTa jury.
"""
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import run

HERE = Path(__file__).resolve().parent
GATE_LABELS = {
    "consent": "Artist consent on record",
    "ai-disclosure": "AI use disclosed",
    "rights": "Rights holder known",
}
ICON = {"selected": "🟢", "needs-review": "🟠", "not-selected": "⚪"}
LABEL = {"selected": "Selected", "needs-review": "Needs human review",
         "not-selected": "Not selected"}
TINT = {"Selected": "#E3F4E8", "Needs human review": "#FFF1DC",
        "Not selected": "#F1F3F5"}


def now():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    st.session_state.log.insert(0, f"{now()}  {msg}")


# ---------------------------------------------------------------- data
def load_data_key(use_csv, csv_text):
    """Return (key, data_text or None, label, errors)."""
    if use_csv and csv_text:
        data_text, n, errors = run.csv_to_metta(csv_text)
        if n:
            key = "csv-" + hashlib.md5(csv_text.encode("utf-8")).hexdigest()[:10]
            return key, data_text, f"your CSV ({n} artworks)", errors
        return "demo", None, "demo data", errors or ["No usable rows in the CSV."]
    return "demo", None, "demo data", []


def ensure_juries(key, data_text, label):
    if st.session_state.get("data_key") != key:
        first_load = "data_key" not in st.session_state
        st.session_state.data_key = key
        st.session_state.jury = run.Jury(data_text)
        st.session_state.base = run.Jury(data_text)  # default rules, for "what changed"
        st.session_state.before = st.session_state.base.evaluate_all()
        st.session_state.cache = {}
        st.session_state.data_label = label
        if not first_load:
            log(f"Loaded {label}")


# ---------------------------------------------------------------- page
st.set_page_config(page_title="Glass Jury", page_icon="🔍", layout="wide")
st.session_state.setdefault("log", [])

# ---- sidebar: data
with st.sidebar:
    st.header("Artworks")
    mode = st.radio("Data source", ["Demo data (12 synthetic works)", "Upload my CSV"],
                    label_visibility="collapsed")
    csv_text = None
    if mode.startswith("Upload"):
        up = st.file_uploader("CSV file", type="csv")
        sample = (HERE / "sample_artworks.csv").read_text(encoding="utf-8")
        st.download_button("Download a sample CSV", sample, "sample_artworks.csv", "text/csv")
        st.caption("Blank cells stay blank. A missing fact is flagged as a gap, never guessed.")
        if up is not None:
            if up.size > 100_000:
                st.error("File is too large (limit 100 KB).")
            else:
                try:
                    csv_text = up.getvalue().decode("utf-8-sig")
                except UnicodeDecodeError:
                    st.error("Please upload a UTF-8 CSV.")
    key, data_text, label, csv_errors = load_data_key(mode.startswith("Upload"), csv_text)
    for e in csv_errors[:5]:
        st.warning(e)
    ensure_juries(key, data_text, label)

jury, base = st.session_state.jury, st.session_state.base
defaults = base.settings()
CRITERIA = base.criteria()

# ---- sidebar: juror challenge
for c in CRITERIA:
    st.session_state.setdefault(f"w_{c}", defaults["weights"][c])
st.session_state.setdefault("thr", defaults["threshold"])
for g in GATE_LABELS:
    st.session_state.setdefault(f"g_{g}", g in defaults["gates"])


def reset_rules():
    for c in CRITERIA:
        st.session_state[f"w_{c}"] = defaults["weights"][c]
    st.session_state["thr"] = defaults["threshold"]
    for g in GATE_LABELS:
        st.session_state[f"g_{g}"] = g in defaults["gates"]
    log("Reset all rules to the defaults")


with st.sidebar:
    st.divider()
    st.header("Juror challenge")
    st.write("Change the rules and watch the verdicts move.")
    weights = {c: st.slider(f"Weight: {c}", 0, 6, key=f"w_{c}") for c in CRITERIA}
    threshold = st.slider("Score needed to be selected", 5, 40, key="thr")
    st.subheader("Hard gates (what-if)")
    st.caption("A gate that fails, or cannot be checked, sends the work to a human. "
               "It is never auto-rejected.")
    gates_on = {g: st.checkbox(lbl, key=f"g_{g}") for g, lbl in GATE_LABELS.items()}
    st.button("Reset to default rules", on_click=reset_rules)

# ---- log rule changes (so every change is visible and attributable)
current = {"weights": dict(weights), "threshold": threshold,
           "gates": {g for g, on in gates_on.items() if on}}
prev = st.session_state.get("prev_settings")
if prev is not None and st.session_state.get("prev_key") == key:
    for c in CRITERIA:
        if prev["weights"][c] != current["weights"][c]:
            log(f"Weight of {c}: {prev['weights'][c]} → {current['weights'][c]}")
    if prev["threshold"] != current["threshold"]:
        log(f"Selection threshold: {prev['threshold']} → {current['threshold']}")
    for g in GATE_LABELS:
        if (g in prev["gates"]) != (g in current["gates"]):
            log(f"Gate '{g}' turned {'ON' if g in current['gates'] else 'OFF (what-if)'}")
st.session_state.prev_settings = current
st.session_state.prev_key = key

# ---- apply the juror's rules to this session's MeTTa jury (as atoms)
for c, w in weights.items():
    jury.set_weight(c, w)
jury.set_threshold(threshold)
for g, on in gates_on.items():
    jury.toggle_gate(g, on)

sig = (tuple(sorted(weights.items())), threshold, tuple(sorted(current["gates"])))
default_sig = (tuple(sorted(defaults["weights"].items())), defaults["threshold"],
               tuple(sorted(defaults["gates"])))
if sig == default_sig:
    st.session_state.cache[sig] = st.session_state.before  # same rules, same answers
elif sig not in st.session_state.cache:
    st.session_state.cache[sig] = jury.evaluate_all()
after = st.session_state.cache[sig]
before = st.session_state.before
b = {r["id"]: r for r in before}

# ---- header
st.title("🔍 Glass Jury")
st.caption("A glass-box jury assistant. Every decision is a MeTTa rule you can inspect "
           f"and challenge. Using {st.session_state.data_label}; all sample data is synthetic.")

with st.expander("How to read this page", expanded=True):
    st.markdown(
        "1. **Results** lists each artwork's verdict, score and flags.\n"
        "2. Open **Why?** to see the full reasoning trail, straight from MeTTa.\n"
        "3. In the sidebar, **challenge the rules** (try raising the weight of "
        "*originality*) and watch **What changed**."
    )

off = [g for g, on in gates_on.items() if not on]
if off:
    st.warning(
        "**What-if mode:** the gate(s) **" + ", ".join(off) + "** are switched off. "
        "Works that would normally go to a human can now be Selected. This is for "
        "exploring how the rules matter, not for real decisions. Every change is logged below.")

# ---- summary tiles
counts = {v: sum(1 for r in after if r["verdict"] == v) for v in ICON}
c1, c2, c3 = st.columns(3)
c1.metric("Selected", counts["selected"])
c2.metric("Needs human review", counts["needs-review"])
c3.metric("Not selected", counts["not-selected"])

# ---- what changed
st.subheader("What changed")
moved = [r for r in after if r["verdict"] != b[r["id"]]["verdict"]]
rescored = [r for r in after
            if r["verdict"] == b[r["id"]]["verdict"] and r["score"] != b[r["id"]]["score"]]
if not moved and not rescored:
    st.info("Rules match the defaults. Change a weight, the threshold or a gate in the sidebar.")
else:
    for r in moved:
        o = b[r["id"]]
        st.success(f"**{r['title']}**: {LABEL[o['verdict']]} ({o['score']}) → "
                   f"**{LABEL[r['verdict']]}** ({r['score']})")
    if rescored:
        with st.expander(f"{len(rescored)} more changed score but kept the same verdict"):
            for r in rescored:
                o = b[r["id"]]
                st.write(f"{r['title']}: {o['score']} → {r['score']} ({LABEL[r['verdict']]})")

with st.expander(f"Rule change log ({len(st.session_state.log)})"):
    if st.session_state.log:
        for line in st.session_state.log[:30]:
            st.text(line)
    else:
        st.caption("No rule changes yet.")

# ---- results table (rows tinted by verdict)
st.subheader("Results")
df = pd.DataFrame(
    [
        {
            "Status": ICON[r["verdict"]],
            "Artwork": r["title"],
            "Verdict": LABEL[r["verdict"]],
            "Score": r["score"],
            "Confidence": r["confidence"],
            "Flags": ", ".join(
                [f"gate {'failed' if g['state'] == 'failed' else 'unverified'}: {g['gate']}"
                 for g in r["gates"]]
                + [f"gap: {c}" for c in r["missing"]]
                + [f"weak: {c}" for c in r["weak"]]
            ) or "-",
        }
        for r in after
    ]
)
st.dataframe(
    df.style.apply(lambda row: [f"background-color: {TINT[row['Verdict']]}"] * len(row), axis=1),
    hide_index=True,
    width="stretch",
)

# ---- the glass box: why?
st.subheader("Why? (the glass box)")
for r in after:
    with st.expander(f"{ICON[r['verdict']]} {r['title']}: {LABEL[r['verdict']]} (score {r['score']})"):
        st.write(f"**{r['outcome_text']}.**")
        for g in r["gates"]:
            if g["state"] == "failed":
                st.error(f"Gate failed: {g['reason']}. Sent to human review.")
            else:
                st.warning(f"Gate could not be checked: {g['reason']}. Sent to human review.")
        st.table([{"Criterion": c, "Weight": str(weights[c]), "Points": str(r["breakdown"][c])}
                  for c in CRITERIA])
        for c in r["missing"]:
            st.warning(f"Gap: no data for '{c}'. It was not guessed, so confidence is reduced.")
        for c in r["weak"]:
            st.info(f"Weak spot: '{c}' is rated low.")
        st.caption(f"Selected if score ≥ {r['threshold']} and no gate fails. "
                   f"Confidence: {r['confidence']}.")
        st.markdown("**Raw MeTTa trace**, the atoms returned by `(why " + r["id"] + ")`:")
        st.code("\n".join(sorted(r["trace"])), language="lisp")

st.divider()
st.caption("Limits: scoring is simple (weight × a three-level rating) and the data is "
           "synthetic. Next step: real data, shared with consent.")