# Romanian camera source catalog

## Registry implementation checkpoint — 2026-11-07

`cameras/romanian-source-registry.json` is now the read-only machine registry for 35
stable camera/directory candidates, and the operator UI retrieves it through authenticated
`GET /api/cameras/discovery`. Registry validation rejects duplicate IDs, non-HTTPS source
pages, enabled candidate ingestion, and directory rows masquerading as camera transports.
Every current row remains ingestion-disabled because a supported processing basis and direct
documented media endpoint are not established. No candidate geometry is asserted; line and
zone arrays are empty unless a calibrated configuration exists.

The Iași profile now declares HLS transport and bounded variant-selection caps. Adapter tests
verify local HLS parsing and FFmpeg-backed decode only; they do not verify the third-party
Iași manifest, current freshness, visible vehicles, permission, or YOLO output. See the latest
implementation checkpoint for test results.

**No candidate is authorized for automated processing based on the evidence currently recorded.**
This is a discovery and permission-tracking catalog, not a list of active feeds. Exact pages were
reviewed on 2026-11-06. The owner-supplied Iași HLS URL received one bounded HEAD and playlist-only
GET; no child playlist or media segment was fetched, no candidate frames were decoded, and no
external video was submitted to YOLO. See [the exact URL audit](EXACT_ROMANIAN_CAMERA_URL_AUDIT.md).

## Bounded follow-up — 2026-11-07

The exact owner-supplied landing pages were rechecked for listing metadata only. The Cluj city page
shows one Piața Unirii and two separate Piața Mihai Viteazu iframe entries; the Iași county page
lists Piața Unirii and Palatul Culturii as well as Gara Pașcani and Vama Sculeni (directory labels,
not observed traffic frames). InfoBuz lists 6 DN1 views, 3 Fetești/A2 views and 3 DN7 views, with
selection-triggered embeds and no processing license found. WebcamRomania and the OpenCam/ARGOS
pages continue to present directory-level claims; no child map feed was decoded. The inspection
tool did not inspect source video. All Romanian entries remain disabled; see the detailed dated
per-link table in `EXACT_ROMANIAN_CAMERA_URL_AUDIT.md`.

The local hardware inventory found no `/dev/video*` node. An explicit owned-UVC adapter profile is
available in `../cameras/local-uvc.yaml`, but the adapter is not an active camera and no hardware
frames were observed. Its onboarding and bounded probe are in `LIVE_CAMERA_OPERATOR_GUIDE.md`.

| Candidate | Area | Public source/provider | Published availability/format | Suitability evidence | Permission | Status |
|---|---|---|---|---|---|---|
| Calea București / Toamnei / 15 Noiembrie | Brașov | [LINX camera page](https://linx.ro/camere-supraveghere-video-internet-giratoriu-calea-bucuresti-toamnei-15-noiembrie-brasov.html) | Page advertises LIVE. LINX says images originate from its monitoring network developed for Brașov municipality. A separate [LINX technical page](https://linx.ro/camere-video-IP-digitale-PTZ.htm) describes the Calea București–Toamnei PTZ as 380,000 pixels and 30 fps with remote pan/tilt; this is a published device claim, not a current preview measurement. | Roundabout offers multiple-trajectory potential; PTZ movement may invalidate fixed geometry; actual visibility/occlusion unknown. High request-for-information priority, not measured rank. | Page includes copyright notice. No processing/recording grant found. | Candidate, disabled; contact LINX/municipality |
| Calea București / Saturn / Poienelor | Brașov | [LINX camera page](https://linx.ro/camere-supraveghere-video-strazi-internet-calea-bucuresti-saturn-brasov.html) | Page advertises LIVE; source page says network developed by LINX for Brașov municipality. Resolution, FPS, and transport not documented. | Roundabout/junction potential; view geometry, angle stability, and vehicle throughput unknown. High request-for-information priority, not measured rank. | No processing/recording grant found. | Candidate, disabled; contact LINX/municipality |
| Piața Mihai Viteazu | Cluj-Napoca | [Municipal live webcam directory](https://primariaclujnapoca.ro/cetateni/live-webcam/) | Municipality page lists two embeds with this name, shown as YouTube iframes; page timestamp is 2026-08-06. No raw processing endpoint documented. | Urban traffic potential; views may differ; lane visibility and vehicle volume unmeasured. | Public display does not establish automated processing/recording permission; ask municipality. | Candidate, disabled; format unresolved |
| DN1: Predeal, Sinaia, Bușteni | National road | [InfoBuz DN1 directory](https://www.infobuz.ro/trafic-romania/dn1/) | Directory lists LIVE/direct-view cameras attributed to WebcamRomania and says feeds load on selection; no machine-ingest format documented. | Roadside corridor potential; per-view geometry, resolution, reliability, and throughput unmeasured. | No automated processing or recording grant found. | Candidate locations only; disabled |
| DN7: Pitești, Râmnicu Vâlcea, Călimănești | National road | [InfoBuz DN7 directory](https://www.infobuz.ro/en/traffic-romania/dn7/) | Directory lists LIVE/direct-view feeds attributed to WebcamRomania; no ingest endpoint documented. | Corridor potential; camera-by-camera suitability and throughput unknown. | No grant found; provider permission required. | Candidate locations only; disabled |
| A2: Fetești | Motorway | [InfoBuz A2 directory](https://www.infobuz.ro/en/traffic-romania/a2/) | Directory lists three Fetești views and labels the source CNAIR Traffic Live; feeds/iframes load only after selection. No direct ingest format documented. | Motorway traffic potential; view geometry and measured throughput unknown. | Directory/embedding does not establish automated processing or recording rights. | Candidate location only; disabled |
| DN17: Ilișești | National road | [WebcamRomania page](https://webcamromania.ro/webcam-orase/webcam-ilisesti-dn17/) | Page labels the camera LIVE and presents images and timelapse; continuous video vs periodically refreshed still, resolution, and FPS unknown. | Roadside candidate; lane coverage and throughput unmeasured. | No grant found. | Candidate, disabled |
| Piața Unirii | Iași | Existing [camera config](../cameras/iasi-piata-unirii.yaml); [WebcamRomania page](https://webcamromania.ro/webcam-orase/webcam-iasi/) | Page locates the camera at Grand Hotel Traian and publishes 47.165489, 27.579009. YAML describes HLS; no feed was contacted in this mission. | Existing calibration is described as rough; lane coverage for vehicle counts is not validated. | Config records `granted: false`. Keep disabled. | Configured but unauthorized/disabled |
| Other national directories | Multiple | [OpenCam](https://opencam.live/cameras/romania), [Argos Atlas](https://argosatlas.com/en/cameras/romania/), [Digi Webcams](https://www.digi.ro/servicii/online/web-cams), [webcam.ro](https://webcam.ro/live) | Directory entries and formats not reviewed individually. | Must assess each candidate independently. | No blanket directory permission. | Discovery only |

## Qualitative inspection order

### Current directory review (2026-11-06)

- WebcamRomania's [traffic directory](https://webcamromania.ro/trafic/) currently lists four
  traffic candidates as “Live” (Predeal Centru DN1, Sinaia DN1, Predeal DN1, Ilișești DN17) and
  displays a most-recent-capture/update clock. This is publisher metadata only: no sequential
  frames, moving-car cadence, direct stream, or machine-processing right was verified.
- The [Predeal DN1 page](https://webcamromania.ro/webcam-munte/webcam-predeal-dn1/) describes a
  traffic view toward Azuga–Bucharest and publishes coordinates 45.5217 N, 25.5379 E. Its page
  labels it LIVE but also exposes a day compressed into a 10-second timelapse. It identifies
  Digi24 as source. Treat it as the strongest next permission inquiry for DN1, not as a proven
  true-live stream. The page's county label says Prahova; Predeal is commonly associated with
  Brașov, so catalog geography needs owner confirmation before import.
- The [Cluj municipal page](https://primariaclujnapoca.ro/cetateni/live-webcam/) lists Piața Unirii
  and two YouTube iframes both named Piața Mihai Viteazu. Its displayed page timestamp is
  2026-08-06. Do not infer currentness, scene contents, direct media URLs, or analytics permission
  from the page.
- The [DIGI webcam directory](https://www.digi.ro/servicii/online/web-cams) lists many urban,
  national-road and mountain-view locations (including Iași, Cluj, Pitești, Predeal and Brașov),
  but does not provide documented machine-ingest formats or automated-analysis authorization in
  the reviewed directory. Contact DIGI/source owners for a documented feed and rights.

No camera page/embed was opened as a media source, no hidden player endpoint was extracted, no
candidate image was run through YOLO, and no third-party stream was ingested. The one owner-supplied
Iași master manifest check is metadata only and does not establish decoded live video. Candidates
remain UNVERIFIED for vehicle imagery; public-page LIVE labels do not meet
`AUTHORIZED_EXTERNAL_LIVE` acceptance.

This is a request-for-information order, **not a numeric camera or traffic ranking**:

1. Brașov LINX roundabouts and A2/Fetești, because the public pages identify traffic-road views and
   the road geometry could support trajectories or throughput measurement.
2. DN1/DN7 corridor views, after identifying each camera owner and obtaining source terms.
3. Cluj municipal views, after clarifying the two similarly named YouTube embeds and whether the
   municipality permits processing beyond public viewing.
4. Iași Piața Unirii, whose source is already configured but explicitly unauthorized and whose
   calibration is rough.

No current vehicle counts or traffic volumes were observed. No exact score is assigned until each
criterion has evidence and a confidence level. A page being available or labeled LIVE is not proof
that its camera is operational now or that its stream can be ingested.

## Exact-source audit checkpoint (2026-11-06)

See [the exact-source audit](EXACT_ROMANIAN_CAMERA_URL_AUDIT.md) for all 16 owner-supplied URL
dispositions and per-candidate stable IDs. In particular:

- LINX identifies each Brașov roundabout as a separate camera page and says the images come from
  a monitoring network developed for Brașov municipality; the pages state copyright protection.
- Cluj municipal page currently lists one Piața Unirii YouTube embed and two separate Piața Mihai
  Viteazu embeds. Their video content was not opened.
- WebcamRomania Iași page lists Piața Unirii, Palatul Culturii, Gara Pașcani and offline Vama
  Sculeni. The supplied Piața Unirii master HLS manifest is reachable and advertises 1080p/20fps;
  variant decode and current moving traffic were not verified. WebcamRomania terms say video feeds
  belong to original owners and are presented through embeds; no machine-analysis grant was found.
- InfoBuz DN1 lists Ploiești, Sinaia, Bușteni, Predeal, Predeal Centru and Ilișești/DN17; A2 lists
  three Fetești camera labels; DN7 lists Pitești A1/DN7, Râmnicu Vâlcea and Călimănești–Căciulata.
  InfoBuz says feeds load on selection and only permitted embeds are configured.
- OpenCam and ARGOS list relevant road/city subsets, but their exact child map records are not
  available in the page text; interactive map requests returned cache-miss failures in the
  inspection tool. Their aggregate counts are not treated as RoadSentinel camera counts.
- DIGI and webcam.ro expose many road and urban labels; these remain source-page candidates, not
  confirmed unique, moving-vehicle streams. All external items are disabled pending scope evidence.

The allowed local demonstration remains a separate `RECORDED REPLAY` loopback stream. It is not an
owned physical camera and not a Romanian external live camera.

## Ranking policy implemented in code

`roadsentinel.camera_ranking` scores 0–5 assessments for visibility, traffic volume, camera angle,
resolution, reliability, road coverage, low occlusion, lighting, and authorization. Incomplete
assessments remain unranked. Processing permission is a hard eligibility gate: it cannot be offset
by a high technical score. Traffic volume must come from an authorized sample window and include
duration and uncertainty; it must never be fabricated.

## Permission record required before activation

Record the granting entity, date, approved purpose and processing method, whether recording,
retention, display, and export are allowed, retention period, source/geographic scope,
license or contract reference, and a locally stored authorization reference. Keep the source
disabled if any required field is missing or expired.

## Local connector validation

The configured-source adapter in `roadsentinel/sources.py` supports local video files (including
MP4), and delegates authorized RTSP/RTSPS and HTTP(S) video transports (including HLS and MJPEG)
to OpenCV/FFmpeg with bounded open/read timeouts. Authorized HTTP(S) still-image endpoints use a
bounded polling reader that rejects redirects and non-image responses. Synthetic/local MP4 decode
is covered by automated tests. This confirms adapter behavior only: no Romanian video feed or iframe
was opened. The owner-supplied Iași HLS master playlist alone was checked as metadata; all external
candidates remain disabled until automated-processing scope is documented.
