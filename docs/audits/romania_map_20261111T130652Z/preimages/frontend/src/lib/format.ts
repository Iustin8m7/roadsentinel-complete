import { format, formatDistanceToNowStrict } from 'date-fns'
import { ro } from 'date-fns/locale'

export const fmtDateTime = (iso: string) => format(new Date(iso), 'dd.MM.yyyy HH:mm:ss', { locale: ro })
export const fmtTime = (iso: string) => format(new Date(iso), 'HH:mm', { locale: ro })
export const fmtAgo = (iso: string) => formatDistanceToNowStrict(new Date(iso), { locale: ro, addSuffix: true })
export const fmtDuration = (sec: number) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
export const pct = (x: number | undefined) => x === undefined ? '—' : `${Math.round(x * 100)}%`
