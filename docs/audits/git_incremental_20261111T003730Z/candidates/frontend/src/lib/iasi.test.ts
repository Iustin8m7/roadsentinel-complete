import { describe, expect, it } from 'vitest'
import { IASI_CAMERAS, iasiCameraName, isDemoCamera } from './iasi'

describe('stock footage marking', () => {
  it('marks every mapped camera except the real public stream', () => {
    for (const id of Object.keys(IASI_CAMERAS)) {
      expect(isDemoCamera(id)).toBe(id !== 'iasi-piata-unirii')
      expect(iasiCameraName(id)?.startsWith('DEMO · ')).toBe(id !== 'iasi-piata-unirii')
    }
  })
  it('leaves cameras outside the map list alone (their names are real places)', () => {
    expect(isDemoCamera('cam-7b2f1aea')).toBe(false)
    expect(iasiCameraName('cam-7b2f1aea')).toBeUndefined()
    expect(isDemoCamera('toString')).toBe(false)
  })
})
