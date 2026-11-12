import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { useAuthStore, defaultLanding } from '@/store/auth'
import { USE_MOCKS } from '@/lib/api'
import { Logo } from '@/assets/brand/Logo'
import { Banner, Button } from '@/components/ui'
import { Field, OtpInput, TextInput } from '@/components/forms'
import { ThemeToggle } from '@/components/ThemeToggle'
import { CalmToggle } from '@/components/CalmToggle'
import { HeroGraph } from '@/components/HeroGraph'
import { KeyRound, ListOrdered, ScanEye, ShieldCheck } from 'lucide-react'

const DEMO_ACCOUNTS = [
  { username: 'admin', label: 'Administrator' },
  { username: 'operator', label: 'Operator' },
] as const

type Step = 'password' | 'mfa' | 'enroll' | 'recovery'

export default function LoginPage() {
  const login = useAuthStore((s) => s.login)
  const verifyMfa = useAuthStore((s) => s.verifyMfa)
  const startMfaEnrollment = useAuthStore((s) => s.startMfaEnrollment)
  const confirmMfaEnrollment = useAuthStore((s) => s.confirmMfaEnrollment)
  const finishMfaEnrollment = useAuthStore((s) => s.finishMfaEnrollment)
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/app'

  const [step, setStep] = useState<Step>('password')
  const [useRecovery, setUseRecovery] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [code, setCode] = useState('')
  const [enrollmentQr, setEnrollmentQr] = useState<string | null>(null)
  const [enrollmentSecret, setEnrollmentSecret] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const mfaRef = useRef<HTMLInputElement>(null)

  useEffect(() => { document.title = 'Autentificare · RoadSentinel' }, [])
  useEffect(() => { if (step === 'mfa' || step === 'enroll') mfaRef.current?.focus() }, [step, useRecovery])

  const done = () => navigate(from === '/' || from === '/app' ? defaultLanding(useAuthStore.getState().user) : from, { replace: true })

  async function onPassword(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!username.trim() || !password) return setError('Completați utilizatorul și parola.')
    setLoading(true)
    const res = await login(username, password, remember)
    setLoading(false)
    if (!res.ok) return setError(res.error || 'Utilizator sau parolă incorectă.')
    if (res.enrollment) {
      const started = await startMfaEnrollment()
      if (!started.ok) return setError(started.error)
      setEnrollmentQr(started.qr)
      setEnrollmentSecret(started.secret)
      setCode('')
      setStep('enroll')
      return
    }
    if (res.mfa) { setStep('mfa'); setCode(''); return }
    done()
  }

  async function acknowledgeRecoveryCodes() {
    setLoading(true)
    const result = await finishMfaEnrollment()
    setLoading(false)
    if (!result.ok) return setError(result.error)
    setRecoveryCodes([])
    setEnrollmentSecret('')
    setEnrollmentQr(null)
    done()
  }

  async function onMfa(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const v = code.trim()
    if (!useRecovery && !/^\d{6}$/.test(v)) return setError('Codul are 6 cifre.')
    if (useRecovery && !v) return setError('Introduceți codul de recuperare.')
    setLoading(true)
    const res = await verifyMfa(useRecovery ? { recovery_code: v } : { code: v })
    setLoading(false)
    if (!res.ok) return setError(res.error || 'Cod incorect.')
    done()
  }

  async function onEnroll(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!/^\d{6}$/.test(code.trim())) return setError('Codul are 6 cifre.')
    setLoading(true)
    const result = await confirmMfaEnrollment(code.trim())
    setLoading(false)
    if (!result.ok) return setError(result.error || 'Cod incorect.')
    setRecoveryCodes(result.recoveryCodes)
    setStep('recovery')
  }

  return (
    <div className="min-h-dvh w-full flex flex-col text-text-primary relative overflow-hidden">
      <HeroGraph />
      <div className="hero-scrim" aria-hidden="true" />
      <header className="relative z-10 flex items-center justify-between px-5 sm:px-10 pt-4">
        <Logo variant="full" size={36} />
        <div className="flex items-center gap-1"><CalmToggle /><ThemeToggle /></div>
      </header>
      <main id="main" className="relative z-10 flex-1 grid lg:grid-cols-[1.15fr_minmax(0,26rem)] gap-8 lg:gap-16 items-center px-5 sm:px-10 py-8 lg:py-12 max-w-[84rem] w-full mx-auto">
        <section className="stagger flex flex-col gap-5 max-w-2xl">
          <p className="eyebrow">Dispecerat · monitorizare rutieră</p>
          <h1 className="font-display font-bold text-[clamp(2.25rem,4.8vw,3.75rem)] leading-[1.04]">
            Vezi ce contează pe drum.<br /><span className="text-gradient">Decizia rămâne a ta.</span>
          </h1>
          <p className="text-base sm:text-lg text-text-secondary max-w-xl">
            RoadSentinel semnalează evenimente rutiere candidate din fluxurile camerelor și le așază într-o coadă ordonată după prioritate. Un operator uman verifică dovada și decide; fiecare decizie rămâne în jurnalul de audit.
          </p>
          <ul className="hidden sm:grid gap-3 text-sm text-text-secondary mt-1">
            {[
              [ListOrdered, 'Coadă de alerte, cele critice primele'],
              [ScanEye, 'Dovezi video cu redactare euristică, marcată clar'],
              [ShieldCheck, 'Decizii umane, cu rol, motiv și urmă de audit'],
            ].map(([Icon, text], i) => {
              const I = Icon as typeof ListOrdered
              return (
                <li key={i} className="flex items-center gap-3">
                  <span className="grid place-items-center w-9 h-9 rounded-lg border border-border bg-panel/70 text-action"><I size={18} aria-hidden="true" /></span>
                  {text as string}
                </li>
              )
            })}
          </ul>
          <p className="font-mono text-xs text-text-muted mt-2 hidden lg:block">Fundalul este o ilustrație decorativă, nu reprezintă date reale.</p>
        </section>

        <div className="rise glass rounded-2xl p-6 sm:p-7 flex flex-col gap-5 w-full max-w-md mx-auto lg:mx-0">
          <div className="flex flex-col gap-1">
            <h2 className="font-display text-2xl font-semibold">{step === 'password' ? 'Autentificare' : step === 'enroll' ? 'Configurează autentificarea' : step === 'recovery' ? 'Salvează codurile de recuperare' : 'Verificare în doi pași'}</h2>
            <p className="text-sm text-text-secondary">{step === 'password' ? 'Intră în contul tău de operator.' : step === 'enroll' ? 'Scanează codul QR cu aplicația de autentificare, apoi introdu codul afișat.' : step === 'recovery' ? 'Păstrează aceste coduri într-un loc sigur. Fiecare poate fi folosit o singură dată.' : 'Introdu codul pentru a continua.'}</p>
          </div>

          {USE_MOCKS && <Banner tone="warn">Mod demonstrativ: conturi și date fictive.</Banner>}

          {step === 'password' ? (
            <form onSubmit={onPassword} noValidate className="flex flex-col gap-4">
              <Field label="Utilizator">
                {(a) => <TextInput {...a} name="username" autoComplete="username" autoFocus value={username} onChange={(e) => setUsername(e.target.value)} />}
              </Field>
              <Field label="Parolă">
                {(a) => <TextInput {...a} name="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />}
              </Field>
              <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer min-h-[var(--target-min)]">
                <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="w-4 h-4 accent-[var(--action)]" />
                Ține-mă minte
              </label>
              {error && <p role="alert" className="text-sm text-critical">{error}</p>}
              <Button type="submit" size="lg" loading={loading} className="w-full">{loading ? 'Se verifică…' : 'Intră'}</Button>
            </form>
          ) : step === 'enroll' ? (
            <form onSubmit={onEnroll} noValidate className="flex flex-col gap-4">
              {enrollmentQr && <img src={enrollmentQr} alt="Cod QR pentru configurarea aplicației de autentificare" className="mx-auto w-52 rounded-lg bg-white p-3" />}
              <details className="text-sm text-text-secondary"><summary className="cursor-pointer">Nu poți scana codul QR?</summary><code className="mt-2 block break-all rounded bg-void p-2 font-mono">{enrollmentSecret}</code></details>
              <Field label="Cod din aplicația de autentificare" hint="Cod cu 6 cifre." error={error}>
                {(a) => <OtpInput {...a} ref={mfaRef} name="enrollment_code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} />}
              </Field>
              <Button type="submit" size="lg" loading={loading} className="w-full">Activează și continuă</Button>
            </form>
          ) : step === 'recovery' ? (
            <div className="flex flex-col gap-4">
              {error && <p role="alert" className="text-critical">{error}</p>}
              <ul className="grid grid-cols-2 gap-2 rounded-lg bg-void p-4 font-mono text-sm">{recoveryCodes.map((item) => <li key={item}>{item}</li>)}</ul>
              <Button type="button" size="lg" className="w-full" loading={loading} onClick={() => void acknowledgeRecoveryCodes()}>Am salvat codurile, continuă</Button>
            </div>
          ) : (
            <form onSubmit={onMfa} noValidate className="flex flex-col gap-4">
              <div className="flex items-center gap-3 rounded-lg border border-border-subtle bg-void/50 p-3 text-sm text-text-secondary">
                <KeyRound size={20} aria-hidden="true" className="text-action shrink-0" />
                {useRecovery ? 'Folosește unul dintre codurile de recuperare salvate.' : 'Deschide aplicația de autentificare și copiază codul curent.'}
              </div>
              <Field
                label={useRecovery ? 'Cod de recuperare' : 'Cod din aplicația de autentificare'}
                hint={useRecovery ? 'Fiecare cod de recuperare poate fi folosit o singură dată.' : 'Cod cu 6 cifre.'}
                error={error}
              >
                {(a) =>
                  useRecovery ? (
                    <TextInput {...a} ref={mfaRef} name="recovery_code" autoComplete="off" autoCapitalize="none" spellCheck={false} value={code} onChange={(e) => setCode(e.target.value)} />
                  ) : (
                    <OtpInput {...a} ref={mfaRef} name="code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} />
                  )
                }
              </Field>
              <Button type="submit" size="lg" loading={loading} className="w-full">Verifică</Button>
              <div className="flex justify-between text-sm">
                <button type="button" className="text-action underline cursor-pointer min-h-[var(--target-min)]" onClick={() => { setUseRecovery(!useRecovery); setCode(''); setError(null) }}>
                  {useRecovery ? 'Folosesc codul din aplicație' : 'Folosesc un cod de recuperare'}
                </button>
                <button type="button" className="text-text-secondary underline cursor-pointer min-h-[var(--target-min)]" onClick={() => { setStep('password'); setPassword(''); setCode(''); setError(null) }}>
                  Înapoi
                </button>
              </div>
            </form>
          )}

          {USE_MOCKS && step === 'password' && (
            <div className="pt-3 border-t border-border-subtle flex flex-col gap-2">
              <span className="text-xs text-text-secondary text-center">Conturi demonstrative</span>
              <div className="grid grid-cols-2 gap-2">
                {DEMO_ACCOUNTS.map((a) => (
                  <Button key={a.username} variant="secondary" size="sm" onClick={() => { setUsername(a.username); setPassword('mock-only-demo'); setError(null) }}>
                    {a.label}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <p className="text-xs text-text-secondary text-center">Accesul este înregistrat în jurnalul de audit.</p>
        </div>
      </main>
    </div>
  )
}
