"""Tests for the Glass Jury rules. Every verdict is computed by MeTTa."""
from collections import Counter

import pytest

import run


@pytest.fixture()
def jury():
    return run.Jury()


def verdicts(j):
    return {r["id"]: r["verdict"] for r in j.evaluate_all()}


# ---- default rules ------------------------------------------------------
def test_default_split(jury):
    counts = Counter(verdicts(jury).values())
    assert counts == {"selected": 3, "needs-review": 6, "not-selected": 3}


def test_default_selected_works(jury):
    v = verdicts(jury)
    assert {a for a, x in v.items() if x == "selected"} == {"a1", "a7", "a12"}


def test_gate_failures_go_to_human_never_rejected(jury):
    v = verdicts(jury)
    for a in ("a2", "a3", "a6", "a9", "a10"):  # failed or unverifiable gate
        assert v[a] == "needs-review"


def test_gate_states(jury):
    rows = {r["id"]: r for r in jury.evaluate_all()}
    assert rows["a3"]["gates"][0]["state"] == "failed"      # consent missing
    assert rows["a9"]["gates"][0]["state"] == "no-record"   # no consent fact at all
    assert rows["a10"]["gates"][0]["state"] == "no-record"  # AI used, disclosure unknown


# ---- gaps are flagged, never guessed ------------------------------------
def test_gap_that_could_change_result_goes_to_human(jury):
    r = jury.evaluate("a8")  # originality missing; best case 22 >= 20
    assert r["missing"] == ["originality"]
    assert r["score"] == 16 and r["best_case"] == 22
    assert r["verdict"] == "needs-review"
    assert r["confidence"] == "reduced"


def test_gap_that_cannot_change_result_is_not_selected():
    data = ('(artwork z1) (title z1 "Low") (ai-used z1 no) (ai-disclosed z1 na) '
            '(consent z1 granted) (rights z1 known) '
            '(theme-fit z1 low) (message z1 low) (provenance z1 low)')
    r = run.Jury(data).evaluate("z1")  # 3+2+2 = 7; best case 13 < 20
    assert r["best_case"] == 13
    assert r["verdict"] == "not-selected"


def test_gap_on_a_clear_pass_stays_selected():
    data = ('(artwork z2) (title z2 "Strong") (ai-used z2 no) (ai-disclosed z2 na) '
            '(consent z2 granted) (rights z2 known) '
            '(theme-fit z2 high) (message z2 high) (provenance z2 high)')
    r = run.Jury(data).evaluate("z2")  # 21 without the gap
    assert r["verdict"] == "selected" and r["confidence"] == "reduced"


# ---- margin and the reasoning trail -------------------------------------
def test_margin(jury):
    assert jury.evaluate("a5")["margin"] == -1   # Neon Elders misses by one point
    assert jury.evaluate("a12")["margin"] == 1


def test_trail_comes_from_why_rule(jury):
    trace = "\n".join(jury.evaluate("a1")["trace"])
    for token in ("(total 25)", "(threshold 20)", "(margin-pts 5)", "(conf high)",
                  "(final-verdict selected)"):
        assert token in trace


# ---- juror challenge ----------------------------------------------------
def test_originality_challenge_flips_two_works(jury):
    before = verdicts(jury)
    jury.set_weight("originality", 4)
    after = verdicts(jury)
    moved = {a for a in after if after[a] != before[a]}
    assert moved == {"a4", "a5"}
    assert after["a4"] == after["a5"] == "selected"
    assert after["a11"] == "not-selected"  # stays out under the challenge


def test_threshold_change(jury):
    jury.set_threshold(26)
    assert Counter(verdicts(jury).values())["selected"] == 0


def test_turning_a_gate_off_is_a_what_if(jury):
    jury.toggle_gate("consent", False)
    v = verdicts(jury)
    assert v["a3"] == "selected" and v["a9"] == "selected"
    jury.toggle_gate("consent", True)
    assert verdicts(jury)["a3"] == "needs-review"


def test_juries_are_independent():
    a, b = run.Jury(), run.Jury()
    a.set_weight("originality", 6)
    assert b.get_weight("originality") == 2


# ---- human decisions ----------------------------------------------------
def test_human_decision_keeps_machine_verdict(jury):
    jury.set_override("a5", "selected", "Strong community voice")
    r = jury.evaluate("a5")
    assert r["verdict"] == "not-selected"        # the machine said so
    assert r["final"] == "selected"              # the human decided
    assert r["override"] == {"verdict": "selected", "reason": "Strong community voice"}
    assert jury.evaluate("a1")["final"] == "selected"  # others untouched


def test_human_decision_can_be_removed_and_replaced(jury):
    jury.set_override("a5", "selected", "first reason")
    jury.set_override("a5", "needs-review", "second reason")
    assert jury.evaluate("a5")["override"]["reason"] == "second reason"
    jury.clear_override("a5")
    r = jury.evaluate("a5")
    assert r["override"] is None and r["final"] == "not-selected"


def test_human_decision_needs_a_reason_and_a_valid_verdict(jury):
    with pytest.raises(ValueError):
        jury.set_override("a5", "selected", "   ")
    with pytest.raises(ValueError):
        jury.set_override("a5", "maybe", "because")
    with pytest.raises(ValueError):
        jury.set_override("nope", "selected", "because")


def test_reason_text_cannot_break_the_rules(jury):
    jury.set_override("a5", "selected", 'bad "quote") (extra; atom')
    r = jury.evaluate("a5")
    assert r["final"] == "selected"
    assert '"' not in r["override"]["reason"] and ")" not in r["override"]["reason"]


# ---- CSV upload ----------------------------------------------------------
def test_csv_blank_cell_becomes_a_gap():
    text = ("id,title,ai_used,ai_disclosed,consent,rights,theme_fit,message,"
            "provenance,originality\n"
            "x1,Test,no,na,granted,known,high,high,high,\n")
    data, n, errors = run.csv_to_metta(text)
    assert n == 1 and not errors
    assert "(originality" not in data
    r = run.Jury(data).evaluate("w-x1")
    assert r["missing"] == ["originality"]


def test_csv_rejects_bad_values_and_ids():
    text = ("id,title,consent,theme_fit\n"
            "1bad,Title,granted,high\n"
            "ok,Title,maybe,high\n")
    data, n, errors = run.csv_to_metta(text)
    assert n == 1                      # only the valid id is loaded
    assert any("id '1bad'" in e for e in errors)
    assert any("consent 'maybe'" in e for e in errors)
    assert "maybe" not in data


def test_csv_title_is_sanitised():
    data, n, _ = run.csv_to_metta('id,title\nq1,"A ""quoted"" (title); x"\n')
    assert n == 1
    assert run.Jury(data).title("w-q1") == "A quoted title x"


def test_csv_needs_id_and_title_columns():
    _, n, errors = run.csv_to_metta("name,score\na,1\n")
    assert n == 0 and errors


def test_sample_csv_loads_and_evaluates():
    text = (run.HERE / "sample_artworks.csv").read_text(encoding="utf-8")
    data, n, errors = run.csv_to_metta(text)
    assert n == 6 and not errors
    v = verdicts(run.Jury(data))
    assert v["w-s1"] == "selected"
    assert v["w-s3"] == "needs-review"  # consent blank, so unverified
    assert v["w-s5"] == "needs-review"  # rights unknown


# ---- close calls: where is a verdict fragile? ---------------------------
def flip_set(r):
    return {(f["criterion"], f["from"], f["to"]) for f in r["flips"]}


def test_close_call_for_work_just_below_the_bar(jury):
    r = jury.evaluate("a5")  # 19 vs 20
    assert r["close_call"]
    assert flip_set(r) == {("theme-fit", "low", "medium"), ("message", "medium", "high")}


def test_close_call_for_work_just_above_the_bar(jury):
    r = jury.evaluate("a12")  # 21 vs 20
    assert r["close_call"]
    assert flip_set(r) == {("theme-fit", "high", "medium"), ("message", "high", "medium"),
                           ("provenance", "medium", "low")}
    assert all(f["delta"] < 0 for f in r["flips"])


def test_robust_verdicts_are_not_close_calls(jury):
    for a in ("a1", "a7", "a4", "a11"):
        assert not jury.evaluate(a)["close_call"]


def test_no_close_call_analysis_when_a_gate_decides(jury):
    r = jury.evaluate("a3")  # consent gate failed: the score is not what decides
    assert r["flips"] == [] and not r["close_call"]


def test_a_flip_really_flips(jury):
    """Apply the suggested change to the data and check the verdict changes."""
    base = (run.HERE / "data.metta").read_text(encoding="utf-8")
    changed = base.replace("(theme-fit a5 low)", "(theme-fit a5 medium)")
    assert run.Jury(base).evaluate("a5")["verdict"] == "not-selected"
    assert run.Jury(changed).evaluate("a5")["verdict"] == "selected"


# ---- consistency checks on human decisions -------------------------------
def test_precedent_conflict_is_flagged(jury):
    jury.set_override("a4", "selected", "Community impact")  # a4 = 16, a5 = 19 not selected
    r = jury.evaluate("a4")
    assert r["conflicts"] == ["a5"]


def test_no_precedent_conflict_when_decision_is_consistent(jury):
    jury.set_override("a5", "selected", "Strong community voice")  # nobody scores higher
    assert jury.evaluate("a5")["conflicts"] == []


def test_overruling_a_gate_is_flagged(jury):
    jury.set_override("a3", "selected", "Consent confirmed by phone")
    r = jury.evaluate("a3")
    assert r["overruled"] == ["consent"]
    assert r["verdict"] == "needs-review" and r["final"] == "selected"


def test_other_works_carry_no_consistency_flags(jury):
    jury.set_override("a4", "selected", "Community impact")
    assert jury.evaluate("a1")["conflicts"] == [] and jury.evaluate("a1")["overruled"] == []