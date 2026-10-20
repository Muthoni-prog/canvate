import hashlib
import json
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
TINT = {"selected": "#E3F4E8", "needs-review": "#FFF1DC", "not-selected": "#F1F3F5"}


def now():
    return datetime.now().strftime("%H:%M:%S")


def log(msg):
    st.session_state.log.insert(0, f"{now()}  {msg}")


def margin_text(m):
    if m == 0:
        return "exactly on the threshold"
    return f"{abs(m)} point{'s' if abs(m) != 1 else ''} " + ("above" if m > 0 else "short of") \
        + " the threshold"


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
            log(f"Loaded {label}. Human decisions were cleared.")


# ---------------------------------------------------------------- human decisions
def record_decision(aid):
    verdict = st.session_state.get(f"ov_v_{aid}")
    reason = st.session_state.get(f"ov_r_{aid}", "")
    try:
        st.session_state.jury.set_override(aid, verdict, reason)
    except ValueError as e:
        st.session_state[f"ov_msg_{aid}"] = str(e)
        return
    st.session_state[f"ov_msg_{aid}"] = ""
    st.session_state[f"ov_r_{aid}"] = ""
    log(f"Human decision on '{st.session_state.jury.title(aid)}': {LABEL[verdict]}. "
        f"Reason: {st.session_state.jury._overrides[aid]['reason']}")


def remove_decision(aid):
    st.session_state.jury.clear_override(aid)
    log(f"Human decision removed from '{st.session_state.jury.title(aid)}'")


def flip_text(f, selected):
    verb = "Raising" if f["delta"] > 0 else "Lowering"
    effect = "would drop it below the threshold" if selected else "would reach the threshold"
    return (f"{verb} **{f['criterion']}** from {f['from']} to {f['to']} "
            f"({f['delta']:+d} points) {effect}.")


def build_audit(after, weights, threshold, gates_on, overrides):
    """One JSON file: the rules in force, every verdict, every human decision."""
    return json.dumps({
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data": st.session_state.data_label,
        "rules_in_force": {"weights": weights, "threshold": threshold,
                           "active_gates": sorted(g for g, on in gates_on.items() if on)},
        "rule_change_log": list(reversed(st.session_state.log)),
        "decisions": [{
            "artwork": r["title"], "id": r["id"], "score": r["score"],
            "margin": r["margin"], "confidence": r["confidence"],
            "machine_verdict": r["verdict"], "final_decision": r["final"],
            "close_call": r["close_call"], "single_step_changes": r["flips"],
            "human_decision": overrides.get(r["id"]),
            "consistency_flags": {"higher_scoring_work_not_selected": r["conflicts"],
                                  "hard_gate_overruled": r["overruled"]},
            "reasoning_trail": sorted(r["trace"]),
        } for r in after],
    }, indent=2, ensure_ascii=False)


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

overrides = jury.overrides()
ov_sig = tuple(sorted((a, o["verdict"], o["reason"]) for a, o in overrides.items()))
sig = (tuple(sorted(weights.items())), threshold, tuple(sorted(current["gates"])), ov_sig)
default_sig = (tuple(sorted(defaults["weights"].items())), defaults["threshold"],
               tuple(sorted(defaults["gates"])), ())
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
        "1. **Results** lists each artwork's verdict, score, margin and flags.\n"
        "2. Open **Why?** to see the full reasoning trail, straight from MeTTa.\n"
        "3. In the sidebar, **challenge the rules** (try raising the weight of "
        "*originality*) and watch **What changed**.\n"
        "4. Disagree with one verdict? In **Why?**, record a **human decision** with a "
        "reason. The machine verdict stays visible beside it."
    )

off = [g for g, on in gates_on.items() if not on]
if off:
    st.warning(
        "**What-if mode:** the gate(s) **" + ", ".join(off) + "** are switched off. "
        "Works that would normally go to a human can now be Selected. This is for "
        "exploring how the rules matter, not for real decisions. Every change is logged below.")

# ---- summary tiles (final decisions: machine verdict, or the human's if one was recorded)
counts = {v: sum(1 for r in after if r["final"] == v) for v in ICON}
c1, c2, c3, c4 = st.columns(4)
c1.metric("Selected", counts["selected"])
c2.metric("Needs human review", counts["needs-review"])
c3.metric("Not selected", counts["not-selected"])
c4.metric("Human decisions", len(overrides))

# ---- what changed (machine verdicts vs. the default rules)
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
st.download_button("Download audit trail (JSON)",
                   build_audit(after, weights, threshold, gates_on, overrides),
                   "glass_jury_audit.json", "application/json",
                   help="Rules in force, every verdict with its reasoning trail, "
                        "every human decision and the change log.")

# ---- where to spend attention: verdicts one rating step from changing
by_id = {r["id"]: r for r in after}
close = [r for r in after if r["close_call"]]
if close:
    st.info(f"**{len(close)} close call{'s' if len(close) != 1 else ''}:** one rating step "
            "would change the verdict for " + ", ".join(f"*{r['title']}*" for r in close)
            + ". These are the decisions worth a second look.")

# ---- results table (rows tinted by final decision)
st.subheader("Results")
rows, tints = [], []
for r in after:
    flags = ([f"gate {'failed' if g['state'] == 'failed' else 'unverified'}: {g['gate']}"
              for g in r["gates"]]
             + [f"gap: {c}" for c in r["missing"]]
             + [f"weak: {c}" for c in r["weak"]])
    if r["best_case"] is not None and r["verdict"] == "needs-review" and not r["gates"]:
        flags.append("gap could change the result")
    if r["close_call"]:
        flags.append("close call")
    if r["conflicts"] or r["overruled"]:
        flags.append("check human decision")
    final = LABEL[r["final"]] + (" (human)" if r["override"] else "")
    rows.append({
        "Status": ICON[r["final"]],
        "Artwork": r["title"],
        "Machine verdict": LABEL[r["verdict"]],
        "Final decision": final,
        "Score": r["score"],
        "Margin": f"{r['margin']:+d}",
        "Confidence": r["confidence"],
        "Flags": ", ".join(flags) or "-",
    })
    tints.append(TINT[r["final"]])
df = pd.DataFrame(rows)
st.dataframe(
    df.style.apply(lambda row: [f"background-color: {tints[row.name]}"] * len(row), axis=1),
    hide_index=True,
    width="stretch",
)
st.caption("Margin is the score minus the threshold. Positive means above the bar.")

# ---- the glass box: why?
st.subheader("Why? (the glass box)")
for r in after:
    aid = r["id"]
    head = (f"{ICON[r['final']]} {r['title']}: {LABEL[r['final']]} "
            f"(score {r['score']}, {r['margin']:+d} vs threshold)")
    with st.expander(head):
        st.write(f"**{r['outcome_text']}.**")
        if r["override"]:
            st.info(f"**Human decision: {LABEL[r['override']['verdict']]}.** "
                    f"Reason: {r['override']['reason']}. "
                    f"The machine verdict was {LABEL[r['verdict']]}.")
            for g in r["overruled"]:
                st.warning(f"This human decision overrules the '{g}' gate. "
                           "It is recorded in the audit trail.")
            for bid in r["conflicts"]:
                o = by_id[bid]
                st.warning(f"Consistency check: *{o['title']}* scores higher ({o['score']} vs "
                           f"{r['score']}) but was not selected. Be ready to explain the "
                           "difference.")
        for g in r["gates"]:
            if g["state"] == "failed":
                st.error(f"Gate failed: {g['reason']}. Sent to human review.")
            else:
                st.warning(f"Gate could not be checked: {g['reason']}. Sent to human review.")
        st.table([{"Criterion": c, "Weight": str(weights[c]), "Points": str(r["breakdown"][c])}
                  for c in CRITERIA])
        for c in r["missing"]:
            st.warning(f"Gap: no data for '{c}'. It was not guessed, so confidence is reduced.")
        if r["best_case"] is not None:
            if r["verdict"] == "needs-review" and not r["gates"]:
                st.warning(f"This gap could change the result: with the best rating the score "
                           f"could reach {r['best_case']} against a threshold of "
                           f"{r['threshold']}. Sent to human review.")
            else:
                st.caption(f"Best case if the gaps were filled: {r['best_case']}.")
        for c in r["weak"]:
            st.info(f"Weak spot: '{c}' is rated low.")
        st.caption(f"Selected if score ≥ {r['threshold']} and no gate fails. "
                   f"This work is {margin_text(r['margin'])}. Confidence: {r['confidence']}.")

        if r["flips"]:
            st.markdown("**What would change this verdict?** (close call)")
            for f in r["flips"]:
                st.write("- " + flip_text(f, r["verdict"] == "selected"))
        elif not r["gates"]:
            st.caption("Not a close call: no single rating step would change this verdict.")

        st.markdown("**Challenge this verdict**")
        if r["override"]:
            st.button("Remove human decision", key=f"ov_rm_{aid}",
                      on_click=remove_decision, args=(aid,))
        else:
            st.selectbox("Your decision", list(LABEL), format_func=LABEL.get,
                         index=list(LABEL).index(r["verdict"]), key=f"ov_v_{aid}")
            st.text_input("Reason (required)", key=f"ov_r_{aid}", max_chars=200,
                          placeholder="Why does the jury decide differently?")
            st.button("Record human decision", key=f"ov_btn_{aid}",
                      on_click=record_decision, args=(aid,))
            if st.session_state.get(f"ov_msg_{aid}"):
                st.error(st.session_state[f"ov_msg_{aid}"])

        st.markdown("**Raw MeTTa trace**, the atoms returned by `(why " + aid + ")`:")
        st.code("\n".join(sorted(r["trace"])), language="lisp")

with st.expander("The rules, exactly as written (rules.metta)"):
    st.caption("This is the whole decision logic. There is nothing else behind the screen.")
    st.code(run.RULES_TEXT, language="lisp")

st.divider()
st.caption("Limits: scoring is simple (weight × a three-level rating) and the data is "
           "synthetic. Human decisions are recorded for this session and exported in the "
           "audit file. Next step: real data, shared with consent.")
