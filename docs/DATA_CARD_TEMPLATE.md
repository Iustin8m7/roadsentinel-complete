# Data card: <dataset name>   (copy to docs/data-cards/<name>.md and fill EVERY field)

A dataset without a completed card may not be used for training or evaluation
(`training/check_dataset.py` refuses). Do not leave placeholders.

## Sources
Where each image/video comes from (camera, URL or recording, dates, how it was captured), counts per source.

## Licence
Licence and terms of each source (name the licence; "free to use" is not an answer). Is use for model training allowed?

## Consent
Who allowed the use (owner of the camera/stream, written permission: date and form), or why none is needed.
Public webcams are not licensed by being public.

## Retention
How long the raw frames are kept, where, who can access them, when they are deleted.

## Redaction
Are faces and number plates blurred in the stored training frames? How (tool/heuristic) and what is known to be missed.
Frames stored unredacted must be marked and access-restricted.

## Labelling
Who labelled, with which guide (`docs/LABELING_GUIDE.md`), how many frames were reviewed by a second person,
what share of the labels are human-checked versus pre-labels from another model (a pre-label-only test set measures
agreement with that model, not accuracy).

## Splits
How train / val / test were separated: by camera and time block (give the blocks and the minimum gap), counts per split,
conditions covered (day, night, rain, fog).

## Known limits
What this dataset does not cover.
