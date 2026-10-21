"""Smoke test: the Streamlit app runs headlessly and a human decision works."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_app_runs_and_shows_default_split():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert metric(at, "Selected") == "3"
    assert metric(at, "Needs human review") == "6"
    assert metric(at, "Not selected") == "3"


def test_originality_challenge_in_the_ui():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.slider(key="w_originality").set_value(4).run()
    assert not at.exception
    assert metric(at, "Selected") == "5"
    assert any("Market Day" in s.value for s in at.success)


def test_human_decision_in_the_ui():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox(key="ov_v_a5").select("selected").run()
    at.text_input(key="ov_r_a5").set_value("Strong community voice").run()
    at.button(key="ov_btn_a5").click().run()
    assert not at.exception
    assert metric(at, "Human decisions") == "1"
    assert metric(at, "Selected") == "4"


def test_human_decision_without_reason_is_refused():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.button(key="ov_btn_a5").click().run()
    assert not at.exception
    assert metric(at, "Human decisions") == "0"
    assert any("reason" in e.value.lower() for e in at.error)


def test_close_calls_are_surfaced_in_the_ui():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("2 close calls" in i.value for i in at.info)


def test_rules_are_visible_in_the_ui():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert any("verdict" in c.value and "gap-potential" in c.value for c in at.code)


def test_precedent_warning_in_the_ui():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.selectbox(key="ov_v_a4").select("selected").run()
    at.text_input(key="ov_r_a4").set_value("Community impact").run()
    at.button(key="ov_btn_a4").click().run()
    assert not at.exception
    assert any("Consistency check" in w.value for w in at.warning)