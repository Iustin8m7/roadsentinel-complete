/** Only recorded media metadata may place an event in a clip; no midpoint guess. */
export function evidenceTiming(sourceTime: number, details: Record<string, unknown>) {
  const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
  const explicit = details.clip_event_offset_s
  const start = details.clip_start_output_s ?? details.clip_start_source_s
  const derived = finite(start) && Number.isFinite(sourceTime) ? sourceTime - start : undefined
  const value = finite(explicit) ? explicit : derived
  const offset = finite(value) && value >= 0 && value <= 90 ? value : undefined
  const rawFps = details.clip_encoded_fps
  const fps = finite(rawFps) && rawFps > 0 && rawFps <= 240 ? rawFps : undefined
  return { eventOffsetSec: offset, fps }
}
