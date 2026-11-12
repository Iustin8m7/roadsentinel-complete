"""Weights & Biases run logging, so every pipeline run is kept and comparable over time.

Enabled automatically when a W&B key is available (WANDB_API_KEY or `wandb login`).
"""
import os
import subprocess
from pathlib import Path

PROJECT = "roadsentinel"


def _has_key():
    netrc = Path.home() / ".netrc"
    return bool(os.environ.get("WANDB_API_KEY")) or (netrc.exists() and "api.wandb.ai" in netrc.read_text())


def _git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def start(cfg, model_name, imgsz, enabled=None):
    # Opt-in: keyframes and annotated video are police evidence, so nothing goes to a third
    # party unless RS_EXPERIMENT_TRACKING=on is set explicitly.
    if os.environ.get("RS_EXPERIMENT_TRACKING", "off") != "on" or enabled is False or (
            enabled is None and not _has_key()):
        print("W&B: dezactivat (RS_EXPERIMENT_TRACKING=on + `wandb login` ca să salvezi rulările).")
        return None
    import wandb

    commit = _git("rev-parse", "--short", "HEAD")
    dirty = bool(_git("status", "--porcelain"))
    return wandb.init(
        project=PROJECT,
        job_type="pipeline",
        name=f"{cfg['id']}-{commit or 'nogit'}{'-dirty' if dirty else ''}",
        tags=[cfg["id"], model_name],
        config={"camera": cfg["id"], "video": cfg["video"], "model": model_name, "imgsz": imgsz,
                "thresholds": cfg["thresholds"], "git_commit": commit, "git_dirty": dirty,
                "git_message": _git("log", "-1", "--format=%s")},
    )


def finish(run, stats, events, speeds, annotated_video):
    if run is None or os.environ.get("RS_EXPERIMENT_TRACKING", "off") != "on":
        return
    import wandb

    table = wandb.Table(columns=["t_s", "priority", "type", "rule", "speed_kmh", "keyframe"])
    for e in events:
        table.add_data(e["video_t"], e["priority"], e["type"], e["rule"], e.get("speed_kmh"),
                       wandb.Image(e["keyframe"]))
    log = {"events_table": table, **{f"stats/{k}": v for k, v in stats.items() if isinstance(v, (int, float))}}
    for k, v in stats["events_by_type"].items():
        log[f"events/{k}"] = v
    if speeds:
        log["vehicle_speed_kmh"] = wandb.Histogram(speeds)
    if Path(annotated_video).exists():
        log["annotated_video"] = wandb.Video(str(annotated_video), format="mp4")
    run.log(log)
    run.summary.update(stats)
    run.finish()
