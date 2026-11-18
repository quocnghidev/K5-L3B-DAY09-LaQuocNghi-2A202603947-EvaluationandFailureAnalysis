"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)
    Beyond the list: duplicated (item, seed) rows, and aggregate metrics that do not match the rows."""
    problems: list[str] = []
    rows = pr.get("rows") or []
    man = pr.get("manifest") or {}

    # 1. NaN / inf aggregate values
    for k, v in (pr.get("metrics") or {}).items():
        if isinstance(v, float) and not math.isfinite(v):
            problems.append(f"metric {k} is {v}")

    # 2. rows dropped or duplicated; the manifest is self-reported, so also compare with the baseline below
    keys = [(r.get("item_id"), r.get("seed")) for r in rows]
    want = int(man.get("items", 0)) * len(man.get("seeds") or [])
    if len(rows) != want:
        problems.append(f"{len(rows)} rows, manifest says {man.get('items')} items x {len(man.get('seeds') or [])} seeds = {want}")
    dup = sorted({k for k in keys if keys.count(k) > 1}, key=str)
    if dup:
        problems.append(f"duplicated (item, seed) rows: {dup[:3]}")

    # 3. same (item, seed) set as the baseline
    bkeys = {(r.get("item_id"), r.get("seed")) for r in base.get("rows") or []}
    if set(keys) != bkeys:
        problems.append(f"(item, seed) set differs from baseline: {len(set(keys) - bkeys)} extra, {len(bkeys - set(keys))} missing")

    # 4. broken graders
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s): {pr['evaluator_failures'][0]}")
    graded = [m["id"] for m in spec.get("metrics", []) if m["id"] in GRADERS]
    bad = [(r.get("item_id"), r.get("seed"), m) for r in rows for m in graded if r.get(m) is None]
    if bad:
        problems.append(f"{len(bad)} row value(s) missing for a graded metric, first {bad[0]}")

    # 5. aggregates must be what the rows say (a hand-edited metrics block would otherwise pass)
    if rows and not bad and graded:
        try:
            fresh = aggregate([{"cost": 0.0, **r} for r in rows], graded, k_values=spec.get("pass_k", []))
            for k, v in fresh.items():
                if k == "cost_per_success":          # cost is not graded evidence; do not recompute it
                    continue
                got = (pr.get("metrics") or {}).get(k)
                if isinstance(v, (int, float)) and isinstance(got, (int, float)) and math.isfinite(got) \
                        and abs(v - got) > 1e-3 * max(1.0, abs(v)):
                    problems.append(f"metric {k}={got} but the rows give {v}")
        except (KeyError, TypeError) as e:
            problems.append(f"cannot recompute metrics from rows: {e!r}")

    # 6. slice tags must match the baseline's
    def tags(rep):
        out: dict = {}
        for r in rep.get("rows") or []:
            out.setdefault(r.get("item_id"), set()).update(r.get("slices") or [])
        return out
    tp, tb = tags(pr), tags(base)
    moved = sorted(i for i in tp.keys() & tb.keys() if tp[i] != tb[i])
    if moved:
        problems.append(f"slice tags differ from baseline for {moved[:3]}")

    # 7. ratchet: on the same eval-set version thresholds may only get stricter
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        problems += _ratchet(spec, base_spec)
    return problems


def _loosened(name: str, new: dict, old: dict) -> list[str]:
    out = []
    ths_new, ths_old = new.get("threshold", new), old.get("threshold", old)
    for key, worse in (("min", lambda n, o: n < o), ("max", lambda n, o: n > o), ("max_increase", lambda n, o: n > o)):
        if key in ths_old and (key not in ths_new or worse(ths_new[key], ths_old[key])):
            out.append(f"{name}: {key} {ths_old[key]} -> {ths_new.get(key)}")
    if ths_old.get("no_significant_drop") and not ths_new.get("no_significant_drop"):
        out.append(f"{name}: no_significant_drop removed")
    if old.get("blocking") and not new.get("blocking"):
        out.append(f"{name}: no longer blocking")
    return out


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    out = []
    new = {m["id"]: m for m in spec.get("metrics", [])}
    for m in base_spec.get("metrics", []):
        if m["id"] not in new:
            out.append(f"ratchet: metric {m['id']} removed")
        else:
            out += [f"ratchet: {x}" for x in _loosened(f"metric {m['id']}", new[m["id"]], m)]
    new_sl = {(s["name"], s["metric"]): s for s in spec.get("slices") or []}
    for sl in base_spec.get("slices") or []:
        key = (sl["name"], sl["metric"])
        if key not in new_sl:
            out.append(f"ratchet: slice {sl['name']}/{sl['metric']} removed")
        else:
            out += [f"ratchet: {x}" for x in _loosened(f"slice {sl['name']}/{sl['metric']}", new_sl[key], sl)]
    return out


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        verdict, note = "ok", ""
        if not a:
            verdict, note = "MISSING", "no rows carry this slice"     # an empty slice must not pass silently
            value = None
        else:
            value = sum(a.values()) / len(a)
            if "min" in sl and value < sl["min"]:
                verdict = "fail"
            keys = sorted(set(a) & set(b))
            if sl.get("no_significant_drop") and keys:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                   n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        bad = verdict in ("fail", "MISSING")
        if bad and sl.get("blocking"):
            blocked.append(f"slice:{name}/{metric}")
        label = "BLOCK" if bad and sl.get("blocking") else ("warn" if bad else "ok")
        shown = "None" if value is None else f"{value:.4f}"
        lines.append(f"  slice:{name}/{metric:<14} {shown:<8} {json.dumps({k: sl[k] for k in ('min',) if k in sl}):<14} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
