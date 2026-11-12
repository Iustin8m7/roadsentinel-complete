#!/usr/bin/env bash
# Downloads the public demo clips (Roboflow supervision sample videos) into data/videos/.
set -euo pipefail
mkdir -p data/videos
for f in vehicles.mp4 vehicles-2.mp4; do
  [ -f "data/videos/$f" ] || curl -sSfL -o "data/videos/$f" "https://media.roboflow.com/supervision/video-examples/$f"
done
ls -lh data/videos
