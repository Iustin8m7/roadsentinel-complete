import { useState } from 'react'
import { Link } from 'react-router'
import { Logo } from '@/assets/brand/Logo'
import './LandingPage.css'

const STEPS = [
  { title: 'Cameră', text: 'O cameră rutieră existentă filmează drumul.' },
  { title: 'Detecție automată', text: 'Programul urmărește vehiculele și observă situațiile periculoase.' },
  { title: 'Alertă cu clip', text: 'Dispecerul primește alerta împreună cu un clip scurt.' },
  { title: 'Decizia dispecerului', text: 'Omul vede clipul și confirmă sau respinge alerta.' },
]

/** Three alerts a visitor finds in the app after signing in, each with a frame from its clip. */
const SHOTS = [
  {
    img: '/landing/viteza.jpg',
    alt: 'Pod rutier noaptea, văzut de sus; o mașină este încadrată cu portocaliu, cu viteza scrisă deasupra.',
    title: 'Viteză foarte mare',
    text: 'O mașină la aproximativ 115 km/h pe un pod unde limita este 50 km/h.',
  },
  {
    img: '/landing/distanta.jpg',
    alt: 'Două mașini pe aceeași bandă de autostradă, una imediat în spatele celeilalte, amândouă încadrate cu portocaliu.',
    title: 'Distanță prea mică',
    text: 'Două mașini una în spatele celeilalte, la peste 130 km/h.',
  },
  {
    img: '/landing/ambuteiaj.jpg',
    alt: 'Pasaj rutier cu trei benzi pline de mașini care abia înaintează, fiecare încadrată cu verde.',
    title: 'Ambuteiaj',
    text: 'O coloană care abia înaintează printr-un pasaj.',
  },
]

type SignKind = 'warns' | 'must' | 'never'
const FACTS: { sign: SignKind; title: string; text: string }[] = [
  {
    sign: 'warns',
    title: 'Ce semnalează',
    text: 'Viteză foarte mare, distanță prea mică între vehicule, ambuteiaj, vehicul oprit pe carosabil, mers pe contrasens, posibil accident.',
  },
  {
    sign: 'must',
    title: 'Cine decide',
    text: 'Omul confirmă sau respinge fiecare alertă, după ce vede clipul. Sistemul doar semnalează.',
  },
  {
    sign: 'never',
    title: 'Viața privată',
    text: 'Fără recunoaștere facială. Estomparea fețelor și a numerelor de înmatriculare există, dar nu este încă aplicată pe toate clipurile. Fiecare vizualizare rămâne în jurnal.',
  },
]

type Decision = 'confirmed' | 'rejected'
const OUTCOME: Record<Decision, { title: string; text: string }> = {
  confirmed: {
    title: 'Alertă confirmată',
    text: 'În aplicație, decizia rămâne în jurnal, cu numele dispecerului.',
  },
  rejected: {
    title: 'Alertă respinsă',
    text: 'Sistemul doar semnalează. Ultimul cuvânt îl are omul, iar respingerea rămâne și ea în jurnal.',
  },
}

/** A person, as road signs draw one: the same figure is required on one sign and crossed out on another. */
const PERSON = 'M32 15a8 8 0 1 1 0 16a8 8 0 0 1 0-16zM16 49c0-9 7-15 16-15s16 6 16 15z'

/** The three families of road signs: a warning, an obligation, a prohibition. */
function Sign({ kind }: { kind: SignKind }) {
  return (
    <svg className="rs-landing-signpost" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
      {kind === 'warns' && (
        <>
          <path d="M32 8L59 55H5z" fill="#fff" stroke="#c8102e" strokeWidth="6" strokeLinejoin="round" />
          <path d="M29.5 24h5l-1 16h-3z" fill="#1c1e20" />
          <circle cx="32" cy="46" r="2.8" fill="#1c1e20" />
        </>
      )}
      {kind === 'must' && (
        <>
          <circle cx="32" cy="32" r="29" fill="#0a4da3" />
          <circle cx="32" cy="32" r="26" fill="none" stroke="#fff" strokeWidth="1.5" />
          <path d={PERSON} fill="#fff" />
        </>
      )}
      {kind === 'never' && (
        <>
          <circle cx="32" cy="32" r="26" fill="#fff" stroke="#c8102e" strokeWidth="6" />
          <path d={PERSON} fill="#1c1e20" />
          <path d="M14 14L50 50" stroke="#c8102e" strokeWidth="6" />
        </>
      )}
    </svg>
  )
}

/** County-road kilometre stone (white, blue cap) carrying the step number. */
function Stone({ n }: { n: number }) {
  return (
    <span className="rs-landing-stone" aria-hidden="true">
      <svg viewBox="0 0 44 56" width="44" height="56">
        <path d="M4 56V20a18 18 0 0 1 36 0v36z" fill="#f3f5f6" />
        <path d="M4 27v-7a18 18 0 0 1 36 0v7z" fill="#0a4da3" />
        <text x="22" y="49" textAnchor="middle" fontSize="20" fontWeight="800" fill="#2b2f33">{n}</text>
      </svg>
    </span>
  )
}

/** Public first screen: what the product is, in plain words, before the login form. */
export default function LandingPage() {
  const [decision, setDecision] = useState<{ kind: Decision; at: string } | null>(null)
  const decide = (kind: Decision) =>
    setDecision({ kind, at: new Date().toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' }) })
  // Someone who asked for less motion gets the still frame and the player's own controls.
  const [still] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false)

  return (
    <div className="rs-landing">
      <header className="rs-landing-wrap rs-landing-top">
        <div className="rs-landing-brand">
          <Logo size={38} />
          RoadSentinel
        </div>
        <span className="rs-landing-temp">Prototip demonstrativ</span>
      </header>

      <main>
        <section className="rs-landing-wrap rs-landing-hero">
          <div className="rs-landing-pitch">
            <h1 className="rs-landing-title">
              <span>Camerele observă drumul.</span>
              <span>Omul decide.</span>
            </h1>
            <p className="rs-landing-lede">
              RoadSentinel urmărește imaginile camerelor rutiere existente și îl anunță pe dispecer când pe drum pare să apară un pericol.
            </p>
            <Link to="/login" className="rs-landing-sign">Intră în aplicație</Link>
          </div>

          <figure className="rs-landing-view">
            <video
              className="rs-landing-clip"
              src="/landing/alerta-viteza.mp4"
              poster="/landing/alerta-viteza.jpg"
              autoPlay={!still}
              controls={still}
              loop
              muted
              playsInline
              aria-label="Clip de exemplu: o autostradă văzută de sus; programul încadrează vehiculele, iar o mașină albă este marcată cu portocaliu, cu viteza scrisă deasupra."
            />
            <div className="rs-landing-slip" data-decision={decision?.kind ?? 'new'} data-testid="landing-alert" aria-live="polite">
              {decision ? (
                <>
                  <h2>{OUTCOME[decision.kind].title}</h2>
                  <p className="rs-landing-stamp">Decizia dumneavoastră, ora {decision.at}</p>
                  <p>{OUTCOME[decision.kind].text}</p>
                  <div className="rs-landing-choices">
                    <button type="button" className="rs-landing-choice" data-kind="quiet" onClick={() => setDecision(null)}>
                      Mai încearcă o dată
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <h2>Viteză foarte mare</h2>
                  <p>Mașina marcată cu portocaliu circulă, după estimarea programului, cu aproximativ 150 km/h.</p>
                  <p className="rs-landing-ask">Dumneavoastră decideți:</p>
                  <div className="rs-landing-choices">
                    <button type="button" className="rs-landing-choice" onClick={() => decide('confirmed')}>Confirmă</button>
                    <button type="button" className="rs-landing-choice" data-kind="quiet" onClick={() => decide('rejected')}>Respinge</button>
                  </div>
                </>
              )}
            </div>
            <figcaption className="rs-landing-caption">
              Exemplu dintr-o filmare de stoc, din altă țară. Viteza este estimată din imagine.
            </figcaption>
          </figure>
        </section>

        <section className="rs-landing-wrap rs-landing-seen" aria-labelledby="landing-seen">
          <h2 id="landing-seen">Trei alerte pe care le găsiți în aplicație</h2>
          <p className="rs-landing-seen-note">Cadre din clipurile pe care le primește dispecerul. Filmări de stoc, din alte țări; vitezele sunt estimate din imagine.</p>
          <div className="rs-landing-shots">
            {SHOTS.map((shot) => (
              <figure key={shot.title} className="rs-landing-shot">
                <img src={shot.img} alt={shot.alt} loading="lazy" width="960" height="540" />
                <figcaption>
                  <h3>{shot.title}</h3>
                  <p>{shot.text}</p>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        <section className="rs-landing-road" aria-labelledby="landing-steps">
          <div className="rs-landing-wrap">
            <h2 id="landing-steps">De la cameră la decizie</h2>
            <ol className="rs-landing-steps">
              {STEPS.map((step, index) => (
                <li key={step.title}>
                  <Stone n={index + 1} />
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="rs-landing-wrap rs-landing-facts">
          {FACTS.map((fact) => (
            <div key={fact.title}>
              <Sign kind={fact.sign} />
              <h2>{fact.title}</h2>
              <p>{fact.text}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="rs-landing-wrap rs-landing-foot">
        <div className="rs-landing-again">
          <p>Alertele de mai sus vă așteaptă în aplicație, cu clipurile lor.</p>
          <Link to="/login" className="rs-landing-sign">Intră în aplicație</Link>
        </div>
        <p>
          <strong>Prototip demonstrativ.</strong>{' '}
          Majoritatea filmărilor sunt imagini de stoc filmate în alte țări, așezate pe harta Iașului doar ca exemplu; un singur flux este real (Piața Unirii). Precizia detecției nu a fost încă măsurată.
        </p>
      </footer>
    </div>
  )
}
