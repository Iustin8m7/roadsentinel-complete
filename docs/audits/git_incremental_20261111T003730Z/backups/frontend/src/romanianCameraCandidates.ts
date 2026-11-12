/** Read-only catalog contract; candidate records are served by the authenticated backend registry. */
export interface RomanianCameraCandidate {
  id: string
  name: string
  road: string
  source: string
  sourcePage: string
  listing: string
  status: "unverified" | "offline" | "replay-only"
  reason: string
  transport: "hls" | "browser_embed" | "timelapse" | "directory" | "unknown"
  adapter: string
  cameraOrDirectory: "camera" | "directory"
  liveStatus: "unknown" | "publisher_offline" | "timelapse"
  actualVehicleVisibility: "unverified" | "yes" | "no"
  processingAuthorization: "not-established" | "authorized"
  ingestionEnabled: boolean
  title: string
  city: string
  roadway: string
  ownerProvider: string
  canonicalPageUrl: string
  canView: boolean
  canEmbed: boolean | null
  canAnalyze: boolean
  canRecord: boolean
  canExport: boolean
  viewingResult: "provider_page_only" | "hls_manifest_only" | "publisher_offline" | "timelapse_page" | "directory_page"
  endpointState: "not_probed" | "master_manifest_reachable" | "snapshot_image_reachable" | "publisher_offline" | "unavailable"
  lastProbe: string | null
  verifiedFrames: number
  sourceLabel: string
  concreteBlocker: string
  playerKind: "official_iframe" | "official_hosted_player" | "supported_hls" | "snapshot" | "unavailable" | "external_link"
  playerUrl: string | null
  sourceKind: "continuous_live" | "refreshed_snapshot" | "recorded_timelapse" | "unknown"
  embeddingPolicy: "supported" | "unsupported" | "unknown" | "not_applicable"
  presentationResult: "documented" | "unavailable" | "unknown"
  presentationFailureReason: string
}

export const romanianCameraTerms = "https://webcamromania.ro/termeni-si-conditii/"
export const infoBuzCameraTerms = "https://www.infobuz.ro/trafic-romania/"
