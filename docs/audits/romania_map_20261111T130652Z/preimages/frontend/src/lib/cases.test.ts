import { afterEach, describe, expect, it, vi } from 'vitest'
import { DEMO_CURATION, HIDDEN_IDS } from './demo'
import { archiveBody, archiveRequest, fmtOffset, newIdempotencyKey, saveSearch, searchArchive, updateFollowup, verifyErrorRo, verifyPackage, type ArchiveRun } from './cases'

afterEach(() => vi.unstubAllGlobals())

describe('archiveBody', () => {
  it('sends trimmed text, filters and cursor', () => {
    expect(archiveBody('  viteză ', { types: ['congestion'], has_evidence: true }, 'abc.def', 10)).toEqual({
      q: 'viteză', filters: { types: ['congestion'], has_evidence: true }, cursor: 'abc.def', limit: 10,
    })
  })
  it('omits empty text and absent cursor', () => {
    expect(archiveBody('   ', {})).toEqual({ filters: {}, limit: 24 })
  })
})

describe('archive runs', () => {
  function capture() {
    const fetcher = vi.fn(async () => new Response('{"results":[],"next_cursor":null,"total":0}', { status: 200 }))
    vi.stubGlobal('document', { cookie: '' })
    vi.stubGlobal('fetch', fetcher)
    return () => (fetcher.mock.calls as unknown as [string, RequestInit][]).map(([, init]) => JSON.parse(String(init.body)))
  }
  const last: ArchiveRun = { q: 'camioane', filters: { types: ['congestion'], has_evidence: true } }
  const edited: ArchiveRun = { q: 'altceva', filters: { statuses: ['new'] } }

  it('load-more reuses the last-run query and filters, ignoring unapplied edits', async () => {
    const bodies = capture()
    const first = archiveRequest(false, last, null, null)
    await searchArchive(first.run.q, first.run.filters, first.cursor)
    const more = archiveRequest(true, edited, last, 'cur.sig')
    expect(more).toEqual({ run: last, cursor: 'cur.sig' })
    await searchArchive(more.run.q, more.run.filters, more.cursor)
    const [a, b] = bodies()
    expect(b).toEqual({ ...a, cursor: 'cur.sig' })
  })
  it('a new search uses the edited values and starts without a cursor', () => {
    expect(archiveRequest(false, edited, last, 'cur.sig')).toEqual({ run: edited, cursor: null })
  })
  it('does not hide operational types or ids when mock curation is off', async () => {
    const bodies = capture()
    await searchArchive('', { has_evidence: true })
    await saveSearch('nume', { has_evidence: true })
    const [search, saved] = bodies()
    expect(search.filters.exclude_types).toEqual([])
    // The demo tenant's curation is a production build flag: off here, so nothing is hidden by id.
    expect(DEMO_CURATION).toBe(false)
    expect(search.filters.exclude_numbers).toEqual([...HIDDEN_IDS].map(Number))
    expect(search.filters.exclude_numbers.length).toBeLessThanOrEqual(500)
    expect(saved.filters).toEqual({ has_evidence: true })
  })
})

describe('helpers', () => {
  it('formats clip offsets', () => {
    expect(fmtOffset(3.25)).toBe('0:03.25')
    expect(fmtOffset(65.5)).toBe('1:05.50')
  })
  it('makes idempotency keys the API accepts', () => {
    expect(newIdempotencyKey()).toMatch(/^[A-Za-z0-9_-]{8,64}$/)
  })
})
describe('investigation completion client', () => {
  it('uploads a package as the raw zip body with CSRF, never as JSON', async () => {
    vi.stubGlobal('document', { cookie: '__Secure-rs_csrf=tok' })
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    vi.stubGlobal('fetch', fetcher)
    const file = new Blob([new Uint8Array([80, 75, 3, 4])], { type: 'application/zip' })
    await verifyPackage(file, 'a'.repeat(64))
    const [url, request] = fetcher.mock.calls[0]
    expect(url).toBe(`/api/exports/verify?manifest_sha256=${'a'.repeat(64)}`)
    expect(request.body).toBe(file)
    expect(request.headers.get('Content-Type')).toBe('application/zip')
    expect(request.headers.get('X-CSRF-Token')).toBe('tok')
  })
  it('sends follow-up changes as PATCH with the revision they are based on', async () => {
    vi.stubGlobal('document', { cookie: '' })
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }))
    vi.stubGlobal('fetch', fetcher)
    await updateFollowup('12', 'f1', { revision: 3, status: 'done' })
    const [url, request] = fetcher.mock.calls[0]
    expect(url).toBe('/api/events/12/followups/f1')
    expect(request.method).toBe('PATCH')
    expect(JSON.parse(request.body)).toEqual({ revision: 3, status: 'done' })
    expect(request.headers.get('Content-Type')).toBe('application/json')
  })
})

describe('verifyErrorRo', () => {
  it('translates known verifier errors and keeps the file name', () => {
    expect(verifyErrorRo('sha256 mismatch: evidence/a.mp4')).toBe('Conținut modificat (amprenta nu corespunde): evidence/a.mp4')
    expect(verifyErrorRo('not a readable zip file: BadZipFile')).toBe('Fișierul nu este o arhivă ZIP care poate fi citită.')
  })
  it('shows an unknown error as received', () => {
    expect(verifyErrorRo('something new')).toBe('something new')
  })
})
