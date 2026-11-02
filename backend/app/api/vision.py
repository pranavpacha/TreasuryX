"""
Computer-vision intelligence endpoints (/api/vision/*) -- five features:
  1. chart digitization        POST /digitize
  2. screenshot comparison     POST /compare
  3. video intelligence        POST /video, /video/demo, GET/DELETE /jobs/{id}   (includes optical flow + frame selection)
  4. visual anomaly detection  POST /anomaly
  5. image quality analyzer    POST /quality
All heavy work runs in the threadpool (never on the event loop); video runs as a cancellable background job.
Nothing here writes Treasury state -- that happens only through the approval flow in vision_review.py.
"""
from __future__ import annotations

import os
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.vision_common import NpResponse, read_image, save_video_temp
from app.cv_engine.preprocessing import to_base64_png
from app.cv_engine.vision import anomaly, compare, digitize, flow, quality, synth, video
from app.cv_engine.vision.jobs import store
from app.database import get_db
from app.models.vision import VisionEvent

router = APIRouter(prefix="/api/vision", tags=["vision"], default_response_class=NpResponse)


# ---------------------------------------------------------------- synthetic sample images (empty-state helper)
@router.get("/sample-image", response_class=Response)
def sample_image(kind: str = "yield_curve", template: int = Query(26, ge=25, le=29), variant: int = Query(1, ge=0, le=4),
                 scale: int = Query(2, ge=1, le=2), anomaly_kind: str | None = Query(None, pattern="^(gap|spike|jump)$")):
    """A SYNTHETIC chart (generator templates 25-29) so every page can be tried without uploading anything."""
    if kind not in synth.KINDS:
        raise HTTPException(400, f"kind must be one of {synth.KINDS}")
    doc = synth.render(kind, template, variant, scale=scale, anomaly=anomaly_kind)
    ok, buf = cv2.imencode(".png", doc.image)
    return Response(buf.tobytes(), media_type="image/png", headers={"X-Synthetic": "true"})


# ---------------------------------------------------------------- 5. quality
@router.post("/quality")
async def quality_analyze(file: UploadFile, with_ocr: bool = True):
    img, _, name = await read_image(file)
    return {"filename": name, **await run_in_threadpool(quality.analyze, img, with_ocr)}


# ---------------------------------------------------------------- 1. digitization
@router.post("/digitize")
async def digitize_chart(file: UploadFile, y_top_value: float | None = Form(None), y_bottom_value: float | None = Form(None),
                         x_left_value: float | None = Form(None), x_right_value: float | None = Form(None)):
    img, _, name = await read_image(file)
    cal = {k: v for k, v in dict(y_top_value=y_top_value, y_bottom_value=y_bottom_value, x_left_value=x_left_value, x_right_value=x_right_value).items() if v is not None} or None
    if cal and (("y_top_value" in cal) != ("y_bottom_value" in cal)):
        raise HTTPException(400, "Manual y calibration needs BOTH y_top_value and y_bottom_value")
    res = await run_in_threadpool(digitize.digitize, img, cal)
    res["filename"] = name
    res["csv"] = digitize.to_csv(res)
    return res


# ---------------------------------------------------------------- 4. comparison
@router.post("/compare")
async def compare_screens(file_a: UploadFile, file_b: UploadFile, with_ocr: bool = True):
    a, _, na = await read_image(file_a)
    b, _, nb = await read_image(file_b)
    res = await run_in_threadpool(compare.compare, a, b, with_ocr)
    return {"filename_a": na, "filename_b": nb, **res}


# ---------------------------------------------------------------- 6. anomaly
@router.post("/anomaly")
async def anomaly_analyze(file: UploadFile, with_ocr: bool = True):
    img, _, name = await read_image(file)
    return {"filename": name, **await run_in_threadpool(anomaly.analyze, img, with_ocr)}


@router.get("/anomaly/sample")
async def anomaly_sample(anomaly_kind: str = Query("gap", pattern="^(none|gap|spike|jump)$"), kind: str = "fx_line_chart", template: int = Query(26, ge=25, le=29), variant: int = Query(1, ge=0, le=4)):
    if kind not in ("fx_line_chart", "yield_curve"):
        raise HTTPException(400, "anomaly samples exist for fx_line_chart and yield_curve")
    doc = synth.render(kind, template, variant, scale=2, anomaly=None if anomaly_kind == "none" else anomaly_kind)
    res = await run_in_threadpool(anomaly.analyze, doc.image, False)
    res["ground_truth"] = {"injected": doc.truth.get("anomaly"), "note": "The anomaly was injected by the synthetic generator, so the expected finding is known."}
    res["source_image"] = to_base64_png(doc.image)
    return res


# ---------------------------------------------------------------- 7. optical flow (sequence of images)
@router.post("/flow")
async def optical_flow(files: list[UploadFile]):
    if not 2 <= len(files) <= 10:
        raise HTTPException(400, "Upload between 2 and 10 frames (in time order)")
    frames = [(await read_image(f))[0] for f in files]
    res = await run_in_threadpool(flow.analyze_sequence, frames)
    res["filenames"] = [f.filename for f in files]
    return res


# ---------------------------------------------------------------- 8. video (background jobs)
def _video_job(path: str, sample_fps: float, max_frames: int, with_ocr: bool, label: str, create_events: bool) -> dict:
    def run(ctx):
        try:
            return video.analyze_video(path, ctx, sample_fps=sample_fps, max_frames=max_frames, with_ocr=with_ocr)
        finally:
            Path(path).unlink(missing_ok=True)
    job = store.submit("video", run, {"label": label, "create_events": create_events})
    return store.public(job, include_result=False)


@router.post("/video")
async def video_upload(file: UploadFile, sample_fps: float = Query(5.0, ge=0.5, le=15), max_frames: int = Query(24, ge=4, le=60), with_ocr: bool = True, create_events: bool = True):
    path = await save_video_temp(file)
    try:
        video.probe(path)
    except ValueError as exc:
        Path(path).unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc
    return _video_job(path, sample_fps, max_frames, with_ocr, file.filename or "video", create_events)


@router.post("/video/demo")
async def video_demo(create_events: bool = True):
    """Generates the SIMULATED terminal clip server-side (no upload) and analyses it. All values in it are simulated."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".avi", prefix="tx_demo_")
    os.close(fd)
    try:
        truth = await run_in_threadpool(video.make_demo_video, path)
    except Exception as exc:  # noqa: BLE001
        Path(path).unlink(missing_ok=True)
        raise HTTPException(503, f"Could not generate demo video: {exc}") from exc
    out = _video_job(path, 5.0, 24, True, "simulated terminal clip", create_events)
    out["meta"]["scripted_truth"] = truth
    return out


@router.get("/jobs/{job_id}")
def job_status(job_id: str, db: Session = Depends(get_db)):
    job = store.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown or expired job")
    out = store.public(job)
    if job["status"] == "done" and job["meta"].get("create_events") and not job["persisted"] and job["kind"] == "video":
        job["persisted"] = True
        n = 0
        for e in job["result"]["events"]:
            if e["severity"] in ("notice", "alert"):
                db.add(VisionEvent(kind=e["kind"], source="video", severity=e["severity"], title=e["title"], detail_json={**e["detail"], "t": e["t"], "frame_index": e["frame_index"]},
                                   source_ref=f"job:{job_id}:{job['meta'].get('label')}"))
                n += 1
        db.commit()
        job["meta"]["events_created"] = n
        out["meta"] = job["meta"]
    return out


@router.delete("/jobs/{job_id}")
def job_cancel(job_id: str):
    job = store.cancel(job_id)
    if job is None:
        raise HTTPException(404, "Unknown or expired job")
    return store.public(job, include_result=False)


