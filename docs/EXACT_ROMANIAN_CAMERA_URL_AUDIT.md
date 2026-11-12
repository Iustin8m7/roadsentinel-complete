# Exact Romanian camera URL audit

## Implementation follow-up — 2026-11-07

The camera candidate metadata is now exposed through the authenticated, read-only
`GET /api/cameras/discovery` route from `cameras/romanian-source-registry.json` (35 stable
candidate/directory records). This is implementation of catalog delivery, not a change in
the findings below: no owner-supplied media endpoint was decoded or activated in this step.
The Iași HLS transport adapter is implemented and locally fixture-tested, but its third-party
playlist/segments remain untested and disabled pending an established processing basis. The
Brașov pages remain unknown transport; Cluj entries remain official-page presentation only;
national-road records remain disabled candidates. No external source is marked live-verified.

Audit date: **2026-11-06**. This is a bounded page/metadata review, not a video-ingestion
authorization or a claim that moving vehicles were visually observed. No third-party video frames
were downloaded, decoded, or submitted to YOLO. All listed external cameras remain disabled.

## Bounded follow-up review — 2026-11-07

The supplied landing pages were re-opened through the available web inspection tool. This is page
metadata only; no third-party media endpoint was opened, no frames were fetched, and no camera was
processed. Current observations:

- LINX pages #1 and #2 still separately identify the two named Brașov roundabout views. Their
  published text says the imagery comes from LINX's monitoring network developed for Brașov
  municipality and says the page content is copyright-protected. This supports the existing
  disabled disposition; it does not establish present moving frames or analysis rights.
- The Cluj-Napoca municipal page enumerates Piața Unirii and two separate Piața Mihai Viteazu
  YouTube iframe entries. Its displayed page content timestamp is 2026-08-06; current embed
  freshness and vehicles were not observed.
- WebcamRomania's Iași page now lists four entries: Piața Unirii, Palatul Culturii, Gara Pașcani
  marked Live by the directory, and Vama Sculeni marked Offline. These are publisher labels, not
  live-frame evidence. Its page describes the Piața Unirii view as pedestrian flow; car visibility
  remains unverified.
- WebcamRomania traffic page lists four publisher-labeled entries: Predeal Centru DN1, Sinaia DN1,
  Predeal DN1 and Ilișești DN17. This does not prove fresh decoded video.
- InfoBuz DN1 text enumerates six views (Ploiești access, Sinaia, Bușteni, Predeal toward Azuga,
  Predeal Centre and Ilișești DN17); it explicitly says video/iframe starts only after selection and
  that feeds appear when permitted for embedding. No feed was selected.
- InfoBuz A2 lists three distinct Fetești direction/camera labels and says feeds load only when
  selected. InfoBuz DN7 lists Pitești A1/DN7, Râmnicu Vâlcea DN7 and Călimănești–Căciulata DN7;
  these publisher-facing labels are not verified unique physical cameras.
- OpenCam's page reports 187 listings, 58 road/city/other and 31 video; ARGOS reports 361 listings,
  302 still feeds and 59 video streams (November 2026). Both remain directory claims; this review
  did not enumerate interactive map children or verify individual media/rights.
- DIGI's page exposes urban and road/mountain directory categories; its interactive map/source
  panels were not inspected camera-by-camera. webcam.ro currently lists a larger text directory
  with road labels including Predeal, Bărcănești DN1, Bușteni DN1, Azuga DN1, Pitești DN7, Lipova,
  Sinaia and Iași Palatul Culturii. `Fără imagine încă` labels remain unavailable listings. None
  establishes automated-processing rights.

Web inspection references captured during this review: LINX #1/#2, Cluj, Iași, WebcamRomania
traffic, InfoBuz DN1/A2/DN7, OpenCam, ARGOS, DIGI and webcam.ro. The source links remain the
canonical evidence and all external cameras remain **disabled**. No source has met the combined
fresh-decoding + visible-vehicles + documented-permitted-processing gate.

## Status definitions

- **DONE / DISABLED WITH EVIDENCE** — page or catalog inspected; disposition and blocking evidence recorded.
- **TEMPORARILY UNAVAILABLE** — the public inspection tool could not retrieve the page/media at this check.
- **BLOCKED BY SPECIFIC EXTERNAL DEPENDENCY** — owner/operator terms do not establish automated-analysis rights or the permitted machine endpoint is not documented.

Publisher `LIVE` badges and catalog timestamps are recorded as publisher claims only. `HLS master
playlist reachable` means a metadata request succeeded; it does not prove that media segments decode,
that frames change, that cars are visible, or that processing is permitted.

## Owner-supplied URL disposition

| # | Exact supplied page | Check result and child cameras found | Rights/technical status | Final status |
|---:|---|---|---|---|
| 1 | [LINX Brașov Calea București / Toamnei / 15 Noiembrie](https://linx.ro/camere-supraveghere-video-internet-giratoriu-calea-bucuresti-toamnei-15-noiembrie-brasov.html) | Page reachable; titled as a live roundabout camera. LINX says imagery comes from the monitoring network developed for Brașov municipality. No camera media was opened, so motion, viewpoint, resolution and cadence remain unverified. | Page states content is copyright protected. No automated-processing grant or documented ingest endpoint found. | **BLOCKED BY SPECIFIC EXTERNAL DEPENDENCY** — owner/municipality must establish processing scope and an allowed endpoint. |
| 2 | [LINX Brașov Saturn / Calea București / Poienelor](https://linx.ro/camere-supraveghere-video-strazi-internet-calea-bucuresti-saturn-brasov.html) | Separate named roundabout; reachable and labeled live. No media opened; current motion and technical details unknown. | Same municipal surveillance network and copyright notice; no machine-processing terms found. | **BLOCKED BY SPECIFIC EXTERNAL DEPENDENCY** |
| 3 | [Cluj-Napoca municipal live webcams](https://primariaclujnapoca.ro/cetateni/live-webcam/) | Page reachable today; lists Piața Unirii and two separately embedded Piața Mihai Viteazu views (three entries total). Their current frame content and vehicle visibility were not checked. The page's displayed content timestamp is 2026-08-06. | YouTube iframe presentation is not an automated-analysis license or a documented ingest path. | **BLOCKED BY SPECIFIC EXTERNAL DEPENDENCY** — municipality/channel terms and processing rights needed. |
| 4 | [WebcamRomania Iași county cameras](https://webcamromania.ro/webcam-live/judetul-iasi/) | Page reachable today; lists Piața Unirii, Palatul Culturii, Gara Pașcani, and Vama Sculeni (marked offline). The precise supplied Piața Unirii URL returned HTTP 200 to one bounded HEAD request and a 183-byte HLS master playlist to one GET. Playlist advertises a 1920×1080, 20 FPS H.264/AAC variant. The child playlist, segments, changing frames, vehicle presence, and decode FPS were not tested. | WebcamRomania's terms say streams belong to original operators and are shown by embed; no machine-processing grant found. Its terms also prohibit aggressive automated scraping and rate-limit bypass. | **BLOCKED BY SPECIFIC EXTERNAL DEPENDENCY** — technically reachable master manifest, but no evidence that this application may process the feed. |
| 5 | [WebcamRomania traffic directory](https://webcamromania.ro/trafic/) | Page reachable today. Lists four publisher-labeled traffic cameras: Predeal Centru DN1, Sinaia DN1, Predeal DN1, Ilișești DN17. Page reports last capture 20:01/update 20:44 at inspection. These are listing metadata, not sequential-frame evidence. | Aggregator terms distinguish the original stream owners; no analytics grant found. | **DONE / DISABLED WITH EVIDENCE** — candidates recorded individually below; not enabled. |
| 6 | [InfoBuz DN1 directory](https://www.infobuz.ro/trafic-romania/dn1/) | Page reachable today; enumerates Ploiești access DN1, Sinaia, Bușteni, Predeal, Predeal Centru, and Ilișești DN17. InfoBuz says camera feeds load only when a selected camera is opened. No feed was opened. Ilișești duplicates the separate DN17 listing. | InfoBuz states cameras appear where embedding is permitted; this is not an analytics/re-recording grant. | **DONE / DISABLED WITH EVIDENCE** — six named entries, five distinct location labels here; rights/transport unresolved. |
| 7 | [WebcamRomania Ilișești DN17](https://webcamromania.ro/webcam-orase/webcam-ilisesti-dn17/) | Page reachable today; publisher labels it LIVE and exposes a still/image view and a “yesterday in 10 seconds” timelapse. No sequential frames or actual update cadence checked. | No automated processing basis found. | **BLOCKED BY SPECIFIC EXTERNAL DEPENDENCY** |
| 8 | [WebcamRomania Ilișești timelapse](https://webcamromania.ro/timelapse/webcam-ilisesti-dn17/) | Direct page request returned a cache-miss error from the web inspection tool. Parent camera page confirms a compressed “yesterday” timelapse feature; it is not continuous live video. | Timelapse reuse rights were not established. | **TEMPORARILY UNAVAILABLE** for direct page inspection; any eventual use is recorded replay and requires rights. |
| 9 | [InfoBuz A2 directory](https://www.infobuz.ro/trafic-romania/a2/) | Page reachable today; enumerates three distinct Fetești camera entries: Camera 1 București→Constanța, Camera 2 București→Constanța, Camera 3 Constanța→București. Feeds are loaded only after selection; no feed opened. | Attributed to CNAIR Trafic Live; page says configured/permitted feeds are embeddable, but no machine-analysis permission was established. | **DONE / DISABLED WITH EVIDENCE** — three entries; rights/transport unresolved. |
| 10 | [InfoBuz DN7 directory](https://www.infobuz.ro/trafic-romania/dn7/) | Page reachable today; enumerates Pitești A1/DN7 area, Râmnicu Vâlcea DN7 area, and Călimănești–Căciulata DN7. No feed opened. | InfoBuz says only cameras allowed for embedding are configured; no separate analytics license found. | **DONE / DISABLED WITH EVIDENCE** — three named entries; rights/transport unresolved. |
| 11 | A1 / Pitești entries within [DN7 directory](https://www.infobuz.ro/trafic-romania/dn7/) and [DIGI directory](https://www.digi.ro/servicii/online/web-cams) | InfoBuz labels one Pitești view as A1/DN7. DIGI lists Pitești Nord, Sud and Centru under national roads. Distinct physical cameras and scene overlap cannot be resolved from text-only catalog labels. | No programmatic ingest/processing grant found. | **DONE / DISABLED WITH EVIDENCE** — directory candidates only; deduplication requires owner/source IDs or authorized preview. |
| 12 | [OpenCam Romania](https://opencam.live/cameras/romania) | Page reachable; it advertises 187 total entries, 58 in “traffic, city and other,” and 31 live-video listings; rest include still images. Place summaries include Bușteni, Sibiu, Brașov, Predeal, Sinaia, Pitești, Galați, Bucharest and Arad. The interactive map links failed with cache-miss responses, so its child camera identities could not be enumerated or deduplicated. | Directory aggregation is not a license from the original stream owners. | **TEMPORARILY UNAVAILABLE** for exhaustive child enumeration; no feeds enabled. |
| 13 | [ARGOS ATLAS Romania](https://argosatlas.com/en/cameras/romania/) | Page reachable; advertises 361 entries: 302 still-image feeds and 59 video streams. It explicitly says most stills refresh every few seconds to minutes. Featured text entries include Buzău Rond Galeria Mall, Alexandria East, Fărcașa Traffic, and Brașov Historical Centre; remaining exact camera list requires interactive map, not exposed in retrieved page. | Directory account/browser access and public visibility do not grant analysis rights. | **TEMPORARILY UNAVAILABLE** for exhaustive child enumeration; all candidates disabled. |
| 14 | [DIGI webcams](https://www.digi.ro/servicii/online/web-cams) | Page reachable today; exposes urban listings for Cluj, Galați, Iași, Sibiu, Râmnicu Vâlcea and others; DN listings include Sebeș, Arad, Lipova, Nădlac, Pitești Nord/Sud/Centru, Bărcănești, Căciulata; mountain listings include Predeal, Brașov, Bușteni and Sinaia. These are distinct directory labels, but the page text does not establish physical uniqueness, roadway visibility, transport, freshness or per-camera terms. | No camera-specific machine endpoint/processing license identified. | **DONE / DISABLED WITH EVIDENCE** — named catalog entries, no machine feeds enabled. |
| 15 | [webcam.ro live directory](https://webcam.ro/live) | Page reachable today; text lists road-relevant labels including Predeal Centre, Bărcănești DN1, Bușteni DN1, Azuga DN1 (listed without image), Pitești DN7 (listed without image), Lipova DN7, Predeal DN1 (RCS-RDS), Pitesti fountains/Primaria, Iași Palatul Culturii, Galați Faleza, and city views. Directory labels alone do not prove visible cars, current frames or unique sources. | No machine-processing license identified. | **DONE / DISABLED WITH EVIDENCE** — metadata only. |
| 16 | [WebcamRomania traffic directory](https://webcamromania.ro/trafic/) (duplicate of #5) | Same four entries and same check; do not count it as a second source. | Same terms/rights limitations. | **DONE / DISABLED WITH EVIDENCE** — deduplicated parent URL. |

## Distinct candidate inventory from accessible text listings

Every entry below is disabled. “Publisher calls it live” is not our verified live state. No external
camera was opened as a video source, so actual vehicle visibility, source FPS, decoder compatibility,
latency, line geometry and tracking suitability all remain **unverified**.

| Stable candidate ID | Distinct listed view | Source page(s) | Publisher/media claim | Processing basis / state |
|---|---|---|---|---|
| RO-BV-LINX-001 | Calea București / Toamnei / 15 Noiembrie roundabout | LINX #1 | Page says LIVE; road geometry suggested by title only | Copyright notice; municipal monitoring network; disabled |
| RO-BV-LINX-002 | Saturn / Calea București / Poienelor roundabout | LINX #2 | Page says LIVE; road geometry suggested by title only | Copyright notice; municipal monitoring network; disabled |
| RO-CJ-MUNI-001 | Piața Unirii | Cluj municipality | YouTube iframe | Current scene unverified; disabled |
| RO-CJ-MUNI-002 | Piața Mihai Viteazu view 1 | Cluj municipality | YouTube iframe | Current scene unverified; disabled |
| RO-CJ-MUNI-003 | Piața Mihai Viteazu view 2 | Cluj municipality | Separate YouTube iframe | Current scene unverified; disabled |
| RO-IS-WCR-001 | Piața Unirii / Grand Hotel Traian | WebcamRomania Iași page; exact HLS supplied by owner | Master playlist HTTP 200; 1920×1080 / 20 FPS advertised only | Original-owner permission absent; disabled |
| RO-IS-WCR-002 | Palatul Culturii, Iași | WebcamRomania Iași page; DIGI also lists Iași urban | Publisher `Live`; roadway visibility unknown | Rights/transport not established; disabled |
| RO-IS-WCR-003 | Gara Pașcani | WebcamRomania Iași page | Publisher `Live`; road view/vehicle flow unknown | Rights/transport not established; disabled |
| RO-IS-WCR-004 | Vama Sculeni | WebcamRomania Iași page | Publisher says Offline | Offline metadata; disabled |
| RO-DN1-WCR-001 | Predeal Centru DN1 | WebcamRomania traffic; webcam.ro; DIGI Predeal Centru aliases possible | `Live` directory labels; identity/frames not confirmed | No processing grant; disabled |
| RO-DN1-WCR-002 | Sinaia DN1 | WebcamRomania traffic; InfoBuz DN1; DIGI Sinaia; webcam.ro Panorama Sinaia | `Live` labels; aliases may overlap, not deduped physically | No processing grant; disabled |
| RO-DN1-WCR-003 | Predeal DN1 toward Azuga/Bucharest | WebcamRomania traffic; InfoBuz; DIGI Predeal; webcam.ro RCS-RDS | `Live` labels; aliases may overlap | No processing grant; disabled |
| RO-DN1-WCR-004 | Bușteni centre / Gara DN1 | InfoBuz DN1; DIGI; webcam.ro | `Live` labels; actual scene unverified | No processing grant; disabled |
| RO-DN1-WCR-005 | Ploiești access / DN1 | InfoBuz DN1 | `Live` directory label | No processing grant; disabled |
| RO-DN1-WCR-006 | Bărcănești DN1 | webcam.ro; DIGI | Directory listing; webcam.ro includes Live label | No processing grant; disabled |
| RO-DN1-WCR-007 | Azuga DN1 | webcam.ro; DIGI | webcam.ro says without image yet; DIGI lists mountain resort | Unavailable/scene unclear; disabled |
| RO-DN17-WCR-001 | Ilișești DN17 | WebcamRomania page/traffic directory; InfoBuz DN1 child list | Publisher says LIVE; yesterday timelapse advertised | No processing grant; disabled |
| RO-DN17-TL-001 | Ilișești prior-day timelapse | WebcamRomania timelapse | Compressed prior-day footage, not true live | Direct page tool cache miss; replay use rights unresolved |
| RO-A2-CNAIR-001 | Fetești camera 1, București→Constanța | InfoBuz A2 | `Live direct`, attributed CNAIR | Permission/endpoint not established; disabled |
| RO-A2-CNAIR-002 | Fetești camera 2, București→Constanța | InfoBuz A2 | `Live direct`, attributed CNAIR | Permission/endpoint not established; disabled |
| RO-A2-CNAIR-003 | Fetești camera 3, Constanța→București | InfoBuz A2 | `Live direct`, attributed CNAIR | Permission/endpoint not established; disabled |
| RO-PIT-INF-001 | Pitești A1/DN7 area | InfoBuz DN7 | `Live direct`, WebcamRomania source | No processing grant; disabled |
| RO-RVL-INF-001 | Râmnicu Vâlcea DN7 area | InfoBuz DN7; DIGI urban Râmnicu Vâlcea | `Live direct` / urban listing; possible alias unresolved | No processing grant; disabled |
| RO-CAL-INF-001 | Călimănești–Căciulata DN7 | InfoBuz DN7; DIGI Căciulata | `Live direct` / resort listing; physical identity unresolved | No processing grant; disabled |
| RO-DIGI-PIT-001 | Pitești Nord | DIGI DN listing | Listing only | No processing grant; disabled |
| RO-DIGI-PIT-002 | Pitești Sud | DIGI DN listing | Listing only | No processing grant; disabled |
| RO-DIGI-PIT-003 | Pitești Centru | DIGI DN listing; overlaps InfoBuz Pitești label possible | Listing only | No processing grant; disabled |
| RO-DIGI-AR-001 | Arad | DIGI DN listing / urban city entry | Listing only | No processing grant; disabled |
| RO-DIGI-AR-002 | Lipova / DN7 | DIGI DN listing; webcam.ro Lipova labels | Listing only; alias likely but unconfirmed | No processing grant; disabled |
| RO-DIGI-AR-003 | Nădlac | DIGI DN listing; webcam.ro RCS-RDS Arad/Lipova/Nădlac label | Listing only; aliases unresolved | No processing grant; disabled |
| RO-DIGI-AB-001 | Sebeș | DIGI DN listing; webcam.ro Sebeș | Listing only | No processing grant; disabled |
| RO-DIGI-PH-001 | Bărcănești | DIGI DN listing; webcam.ro DN1 | Listing only | No processing grant; disabled |
| RO-OPENCAM-MAP | Road/city category, 58 entries per OpenCam page | OpenCam #12 | Mix of live video, snapshots, city/other; identities need interactive map | Map child requests cache-missed; cannot enumerate, disabled |
| RO-ARGOS-MAP | Romania map entries | ARGOS #13 | 302 stills and 59 videos per directory; featured examples not exhaustive | Remaining identities behind map; disabled |
| RO-WEBRO-MAP | Remaining road-relevant city entries | webcam.ro #15 | Directory contains city/road labels; full physical dedup cannot be inferred | Catalog-only; disabled |

The table deliberately does not convert similarly named directory entries into confirmed aliases.
Owner/operator IDs, permitted previews, or documented camera metadata are needed for reliable
physical deduplication. No candidate meets all three enable gates (vehicle relevance, decodable
current source, documented permission to analyze).

## Exact Iași endpoint check details

At 2026-11-06, one `curl -I --max-time 8 --connect-timeout 4` to the exact owner-provided playlist
returned HTTP/2 200, `content-type: application/vnd.apple.mpegurl`, `content-length: 183`. A single
GET of the exact playlist returned `#EXTM3U` and a master variant declaration with 1920×1080,
20.000 FPS, H.264/AAC and an advertised bandwidth of 2.67 Mbps. The variant playlist and media
segments were intentionally not requested. Thus this is a **reachable HLS master manifest**, not
a verified decodable/live feed. The local source adapter continues to fail closed because
`cameras/iasi-piata-unirii.yaml` has `enabled: false` and `source_consent.granted: false`.

## Reproduction and next human action

The Iași metadata-only requests were:

```bash
curl -I --max-time 8 --connect-timeout 4 \
  'https://w1.webcamromania.ro/piatauniriiiasi/index.m3u8'
curl --silent --show-error --max-time 8 --connect-timeout 4 \
  'https://w1.webcamromania.ro/piatauniriiiasi/index.m3u8'
```

The first sandbox request failed DNS resolution; the commands were then run with narrowly approved
network access. The GET typo on the first attempt returned `Not found`; the exact corrected URL
returned the master playlist shown above. No media segment or image was downloaded.

For every disabled candidate, the next action is to obtain the original owner's documented scope
for automated inference, allowed protocol/rate, transient frame handling, preview display, storage
and retention. If a source's terms already grant this, record that exact applicable provision and
source identity; an individual letter is not required when other valid authorization exists. Then
run a short bounded decoder/freshness test and only then create/enable a worker configuration.
