import { expect, it } from 'vitest'
import { evidenceTiming } from './evidenceTiming'

it('places a truncated beginning event at its actual offset instead of midpoint', () => {
  expect(evidenceTiming(.5, {clip_start_output_s:0, clip_encoded_fps:3})).toEqual({eventOffsetSec:.5,fps:3})
})
it('uses the actual encoded event-frame offset for irregular live sampling', () => {
  expect(evidenceTiming(20, {clip_start_source_s:17,clip_event_offset_s:2.5,clip_encoded_fps:2})).toEqual({eventOffsetSec:2.5,fps:2})
})
it('does not fabricate an event position or cadence from missing or invalid metadata', () => {
  expect(evidenceTiming(10, {})).toEqual({eventOffsetSec:undefined,fps:undefined})
  expect(evidenceTiming(10, {clip_start_source_s:20,clip_encoded_fps:Infinity})).toEqual({eventOffsetSec:undefined,fps:undefined})
})
