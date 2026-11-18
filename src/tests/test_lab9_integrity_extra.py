"""Own traps beyond the public four: the instructor grades with hidden ones, so the gate must be general.
Each test hands the gate a report or spec that hides a regression and asserts it is blocked.
Run: python -m pytest -q -m student -o addopts= tests/test_lab9_integrity_extra.py"""
import copy
import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.student
BASE_P, SPEC_P = Path("reports/baseline_v2.json"), Path("config/metric_spec_v2.yaml")
needs = pytest.mark.skipif(not BASE_P.is_file(), reason="baseline_v2 not generated")


@pytest.fixture(scope="module")
def world():
    from lab9.eval import load_spec, run_eval
    from lab9 import variants

    variants.register()
    spec = load_spec(SPEC_P)
    return spec, json.loads(BASE_P.read_text(encoding="utf-8")), run_eval("slice_regression", spec)


def blocked(pr, base, spec, base_spec=None):
    from lab9 import gate

    return gate.check(pr, base, spec, base_spec)[0]


@needs
def test_duplicated_good_rows_replace_failing_ones(world):
    """Same row count as the manifest says, but the failing rows are overwritten by copies of passing ones."""
    spec, base, pr = world
    t = copy.deepcopy(pr)
    good = [r for r in t["rows"] if r["pass_rate"]]
    t["rows"] = [r if r["pass_rate"] else copy.deepcopy(good[0]) for r in t["rows"]]
    assert "integrity" in blocked(t, base, spec)


@needs
def test_hand_edited_metrics_block(world):
    spec, base, pr = world
    t = copy.deepcopy(pr)
    t["metrics"] = dict(base["metrics"])
    assert "integrity" in blocked(t, base, spec)


@needs
def test_relabelled_slices_block(world):
    spec, base, pr = world
    t = copy.deepcopy(pr)
    for r in t["rows"]:
        r["slices"] = [s for s in r["slices"] if s != "money_movement"]
    assert "integrity" in blocked(t, base, spec)


@needs
def test_evaluator_failures_on_green_run_block(world):
    spec, base, _ = world
    t = copy.deepcopy(base)
    t["evaluator_failures"] = ["E-001@11:ApprovalBypass:boom"]
    assert "integrity" in blocked(t, base, spec)


@needs
@pytest.mark.parametrize("edit", ["drop_slice", "non_blocking", "drop_no_sig_drop", "drop_metric", "raise_max"])
def test_ratchet_variants(world, edit):
    spec, base, _ = world
    loose = copy.deepcopy(spec)
    if edit == "drop_slice":
        loose["slices"] = loose["slices"][:-1]
    elif edit == "non_blocking":
        loose["slices"][0]["blocking"] = False
    elif edit == "drop_no_sig_drop":
        loose["slices"][0].pop("no_significant_drop")
    elif edit == "drop_metric":
        loose["metrics"] = [m for m in loose["metrics"] if m["id"] != "pass_hat_5"]
    else:
        next(m for m in loose["metrics"] if m["id"] == "approval_bypass")["threshold"]["max"] = 3
    assert "integrity" in blocked(copy.deepcopy(base), base, loose, spec)


@needs
def test_stricter_spec_is_allowed(world):
    spec, base, _ = world
    strict = copy.deepcopy(spec)
    strict["slices"][0]["min"] = 0.95
    assert blocked(copy.deepcopy(base), base, strict, spec) == []
