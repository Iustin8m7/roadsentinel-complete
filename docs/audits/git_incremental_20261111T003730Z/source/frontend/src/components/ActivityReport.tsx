interface Row { label: string; count: number }

export interface ActivityReportProps {
  period: string
  generatedAt: string
  totals: Row[]
  cameras: Row[]
  types: Row[]
  /** Alert count per hour of day, 24 entries. */
  hours: number[]
}

const heading = 'text-[9pt] font-bold uppercase tracking-wider border-b border-black pb-1 mb-1.5'

function CountTable({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <div>
      <h2 className={heading}>{title}</h2>
      {rows.length === 0 ? <p className="text-[9pt]">Nicio alertă.</p> : (
        <table className="w-full border-collapse text-[9pt]">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b border-neutral-300">
                <td className="py-[3px] pr-2">{row.label}</td>
                <td className="py-[3px] text-right font-mono font-semibold w-12">{row.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/** One A4 page shown only in print (see the print block in index.css). */
export function ActivityReport({ period, generatedAt, totals, cameras, types, hours }: ActivityReportProps) {
  const maxHour = Math.max(1, ...hours)
  return (
    <section className="rs-print-report hidden print:block bg-white text-black font-sans text-[10pt] leading-snug">
      <h1 className="text-[18pt] font-bold tracking-tight">RoadSentinel – raport de activitate</h1>
      <p className="mt-1 text-[10pt]">Perioada acoperită de date: <strong>{period}</strong></p>
      <p className="text-[8.5pt] text-neutral-600">Raport generat la {generatedAt}</p>

      <div className="mt-4 grid grid-cols-4 gap-2">
        {totals.map((total) => (
          <div key={total.label} className="border border-neutral-400 rounded px-2.5 py-2">
            <div className="text-[8pt] uppercase tracking-wider text-neutral-600">{total.label}</div>
            <div className="text-[18pt] font-bold font-mono leading-tight">{total.count}</div>
          </div>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-6">
        <CountTable title="Alerte pe cameră" rows={cameras} />
        <CountTable title="Alerte pe tip" rows={types} />
      </div>

      <div className="mt-5">
        <h2 className={heading}>Alerte pe oră (ora din zi, 00–23)</h2>
        <div className="flex items-end gap-[3px] h-[30mm] mt-2">
          {hours.map((count, hour) => (
            <div key={hour} className="flex-1 h-full flex flex-col justify-end items-center">
              <span className="text-[7pt] font-mono">{count || ''}</span>
              <div className="w-full bg-neutral-700" style={{ height: `${(count / maxHour) * 80}%` }} />
            </div>
          ))}
        </div>
        <div className="flex gap-[3px] border-t border-black pt-0.5">
          {hours.map((_, hour) => (
            <span key={hour} className="flex-1 text-center text-[7pt] font-mono">{String(hour).padStart(2, '0')}</span>
          ))}
        </div>
      </div>

      <p className="mt-6 pt-2 border-t border-neutral-400 text-[8.5pt] text-neutral-700">
        Date demonstrative dintr-un prototip. Nu reprezintă statistici oficiale de trafic.
      </p>
    </section>
  )
}
