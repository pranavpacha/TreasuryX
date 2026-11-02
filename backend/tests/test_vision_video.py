"""Video intelligence (feature 8), frame selection (feature C) and the background job runner."""
from __future__ import annotations

import time

import numpy as np
import pytest

from app.cv_engine.vision import jobs, video
from tests.vision_helpers import needs_ocr


@pytest.fixture(scope="module")
def demo_video(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("vid") / "demo.avi")
    truth = video.make_demo_video(path)
    return path, truth


def test_frame_selector_keeps_changes_and_drops_redundant_frames():
    a, b = video._terminal_frame(1.0), video._terminal_frame(4.0)
    sel = video.FrameSelector()
    for i in range(10):
        sel.consider(i, i / 5, a)                      # 10 identical frames
    for i in range(10, 14):
        sel.consider(i, i / 5, b)                      # screen changes and stays changed
    sel.finish()
    assert [r["idx"] for r in sel.kept] == [0, 11]     # first frame + the first SETTLED changed frame (10 differs from 9, 11 matches 10)
    assert sel.kept[1]["score"] > video.CHANGE_PCT


def test_frame_selector_waits_for_screen_to_settle():
    a, b, c = video._terminal_frame(1.0), video._terminal_frame(8.5), video._terminal_frame(4.0)
    sel = video.FrameSelector()
    sel.consider(0, 0, a)
    sel.consider(1, 0.2, b)        # big change, still moving (next frame differs again)
    sel.consider(2, 0.4, c)        # differs from previous sample too -> not settled
    sel.consider(3, 0.6, c)        # settled
    sel.finish()
    assert [r["idx"] for r in sel.kept] == [0, 3]


def test_prune_respects_budget_and_keeps_first_and_last():
    recs = [{"idx": i, "score": float(s)} for i, s in enumerate([100, 1, 9, 2, 8, 3, 50])]
    kept = video.prune(recs, 4)
    assert [r["idx"] for r in kept] == [0, 2, 4, 6]   # first, last, and the two highest-scoring in between, in time order


@needs_ocr
def test_demo_video_timeline_matches_scripted_events(demo_video):
    path, truth = demo_video
    r = video.analyze_video(path)
    st = r["stats"]
    assert st["frames_selected"] < st["frames_sampled"] / 4 and st["ocr_spared_pct"] > 70
    ev = r["events"]
    vc = [e for e in ev if e["kind"] == "value_change"]
    ten = next(e for e in vc if e["detail"]["instrument"] == "10Y")
    assert (ten["detail"]["from"], ten["detail"]["to"]) == (6.85, 7.02) and ten["detail"]["confirmed_in_next_frame"] is True
    assert abs(ten["t"] - 3.0) <= 0.7
    assert any(e["detail"]["instrument"] == "USD/INR" and e["detail"]["to"] == 83.41 for e in vc)
    assert any(e["kind"] == "scene_change" and abs(e["t"] - 8.0) <= 0.7 for e in ev)
    motion = next(e for e in ev if e["kind"] == "chart_motion")
    assert abs(motion["t"] - 10.0) <= 0.7 and motion["detail"]["median_shift_px"] < -20 and "does not establish market direction" in motion["detail"]["caveat"]
    assert [e["t"] for e in ev] == sorted(e["t"] for e in ev), "timeline must be chronological"
    assert r["selection_policy"]["reinforcement_learning"] is False
    assert all("thumbnail" in f for f in r["frames"])


def test_video_without_ocr_still_selects_frames_and_reports_no_values(demo_video):
    r = video.analyze_video(demo_video[0], with_ocr=False)
    assert r["tracks"] == {} and r["stats"]["ocr_calls"] == 0 and r["stats"]["frames_selected"] >= 4


def test_probe_rejects_corrupt_video(tmp_path):
    bad = tmp_path / "bad.avi"
    bad.write_bytes(b"not a video" * 100)
    with pytest.raises(ValueError):
        video.probe(str(bad))


# ------------------------------------------------------------------ jobs
def test_job_runs_reports_progress_and_returns_result():
    def fn(ctx):
        for i in range(5):
            ctx.progress((i + 1) / 5, f"step {i}")
        return {"ok": True}
    j = jobs.store.submit("t", fn)
    for _ in range(100):
        if j["status"] in ("done", "failed"):
            break
        time.sleep(0.02)
    assert j["status"] == "done" and j["progress"] == 1.0 and j["result"] == {"ok": True}


def test_job_cancellation_and_failure_are_graceful():
    def slow(ctx):
        for _ in range(500):
            time.sleep(0.01)
            ctx.check()
    j = jobs.store.submit("t", slow)
    time.sleep(0.05)
    jobs.store.cancel(j["id"])
    for _ in range(100):
        if j["status"] != "running":
            break
        time.sleep(0.02)
    assert j["status"] == "cancelled"
    bad = jobs.store.submit("t", lambda ctx: 1 / 0)
    for _ in range(100):
        if bad["status"] != "queued" and bad["status"] != "running":
            break
        time.sleep(0.02)
    assert bad["status"] == "failed" and "ZeroDivisionError" in bad["error"]


def test_job_store_is_bounded():
    for _ in range(jobs.MAX_JOBS + 10):
        jobs.store.submit("t", lambda ctx: None)
    time.sleep(1.0)                                    # let the queue drain: only FINISHED jobs can be evicted
    jobs.store.submit("t", lambda ctx: None)
    assert len(jobs.store._jobs) <= jobs.MAX_JOBS + 1
