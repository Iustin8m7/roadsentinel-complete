# Local live camera onboarding

## Current verified hardware state

Bounded local check:

```bash
timeout 15s .venv/bin/python -m scripts.probe_uvc_camera --device-index 0 --seconds 3
```

It exited **2** with `CAMERA_UNAVAILABLE: camera device /dev/video0 is missing`. There is no
physical-camera YOLO/browser proof yet. Connect an operator-owned UVC webcam and ensure Linux
exposes `/dev/videoN`. Do not point it at public space unless the applicable privacy and processing
basis is established.

## Plug-and-check

1. Connect the owned USB camera.
2. Run `ls -l /dev/video*`; optionally use `v4l2-ctl --list-devices` if already installed.
3. Probe only the chosen index: `timeout 20s .venv/bin/python -m scripts.probe_uvc_camera
   --device-index 0 --seconds 5`. The probe retains no frame. Changed pixels do not establish that
   vehicles are present.
4. `cameras/local-uvc.yaml` uses explicit `device:0`, no replay fallback, no fabricated geometry,
   and no incident rules. Detection/tracking can run without calibration; speed and spatial rules
   require measured, camera-specific geometry.
5. Run the existing pipeline in supervised `--live` mode after the device is available and the
   local signed-ingest configuration is set. A missing device fails closed.

The shell `timeout` is the hard bound if a V4L2 driver blocks inside OpenCV. No device was available
here, so source cadence, vehicles, actual inference, preview, API and PostgreSQL remain unverified.
The loopback MP4/MJPEG pipeline remains `RECORDED REPLAY`, not physical live.

## Network cameras

Do not put credentials in source URLs. Network feeds require the existing documented consent record
and explicit enablement. Romanian candidates remain disabled until a valid processing basis and
permitted endpoint are established; public viewing is not treated as an analytics grant.
