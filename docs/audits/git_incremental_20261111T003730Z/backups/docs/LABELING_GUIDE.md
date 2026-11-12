# Labelling guide (detector training and evaluation data)

Format: YOLO txt, one line per object: `class cx cy w h`, all normalised to 0..1, COCO class ids kept
(0 person, 1 bicycle, 2 car, 3 motorcycle, 5 bus, 7 truck). One `.txt` per image; an image with nothing to label has an
empty file (a missing file is an error, not "no objects").

## What to box
* Every vehicle and person that is **at least ~20 px tall** in the frame and **more than ~50 % visible**. Ignore tiny or heavily cut objects consistently, in all splits.
* The **tight box around the visible object** (not the shadow, not the occluded estimate). Boxes touching the frame edge are labelled for the visible part.
* **Occupants**: people inside vehicles are not labelled (the pipeline drops them). Riders on motorcycles/bicycles: label the vehicle and the rider as `person`.
* **Trams** are not buses. Until a `tram` class exists, do not label trams as `bus`; mark the frame in the notes and keep it out of the test set. (The current model confuses them: `docs/RULES.md`, `crash_ignore_classes`.)
* Parked vehicles are labelled like moving ones.
* Debris/objects on the road are **not** in the class map; they need a new class and a decision (roadmap).

## Quality control
1. Pre-labels from another model are a starting point only. A **human must review every frame of the test set**; for train/val review at least a random 10 % and record the error rate.
2. A second person re-labels a random 5 % of the test set; disagreement above 10 % of boxes means the guide is unclear: fix the guide, re-label.
3. Never touch a test frame after a model has been trained on the split; add new frames to a new test set instead.

## Splits (leakage)
Split by **camera and time block**, never by random frames: neighbouring frames of one recording are near-duplicates and
make a model look better than it is. Keep ≥ 10 minutes (more for slow scenes) between any train/val frame and any test frame
of the same camera. Record capture times in the manifest (`training/make_manifest.py`) and run `training/check_dataset.py`.

## Conditions
Tag each item (`day`, `night`, `rain`, `fog`, `glare`). A condition with no tagged test frames is **not evaluated**; say so.

## Privacy
Stored training frames of public places contain faces and plates. Blur them in the stored copies unless the data card
documents consent and restricted access (`docs/DATA_CARD_TEMPLATE.md`).
