import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ChevronLeft, ChevronRight, FileText } from 'lucide-react'
import { Dialog } from './Dialog'
import { Button } from './ui'
import { EvidencePlayer } from './EvidencePlayer'

export interface ModalClip {
  id: string
  title: string
  subtitle?: string
  src?: string
  poster?: string
  at: string
  chip?: ReactNode
}

/** Evidence player in a modal dialog (focus trapped, Esc closes), with previous / next clip navigation. */
export function ClipModal({ clips, start = 0, onClose }: { clips: ModalClip[]; start?: number; onClose: () => void }) {
  const [i, setI] = useState(start)
  const clip = clips[i]
  if (!clip) return null
  return (
    <Dialog open title={clip.title} onClose={onClose} wide>
      <div className="flex flex-wrap items-center justify-between gap-2 -mt-2">
        {clip.subtitle && <p className="text-sm text-text-secondary">{clip.subtitle}</p>}
        <div className="flex items-center gap-2 ml-auto">
          <Button size="sm" variant="secondary" disabled={i === 0} onClick={() => setI(i - 1)} aria-label="Clipul anterior"><ChevronLeft size={16} aria-hidden="true" /></Button>
          <span className="text-sm tabular-nums text-text-secondary" aria-live="polite">{i + 1} / {clips.length}</span>
          <Button size="sm" variant="secondary" disabled={i === clips.length - 1} onClick={() => setI(i + 1)} aria-label="Clipul următor"><ChevronRight size={16} aria-hidden="true" /></Button>
          <Link to={`/app/alerte/${clip.id}`} className="inline-flex items-center gap-1.5 px-3 min-h-[var(--target-min)] rounded-md bg-accent text-on-accent text-sm font-medium">
            <FileText size={14} aria-hidden="true" /> Dosar alertă
          </Link>
          <Button size="sm" variant="secondary" onClick={onClose}>Închide</Button>
        </div>
      </div>
      <div className="h-[60dvh] min-h-72">
        <EvidencePlayer
          key={clip.id}
          src={clip.src}
          poster={clip.poster}
          title={clip.title}
          eventLabel={clip.title}
          downloadName={`alerta_${clip.id}.mp4`}
          chip={clip.chip}
        />
      </div>
    </Dialog>
  )
}
