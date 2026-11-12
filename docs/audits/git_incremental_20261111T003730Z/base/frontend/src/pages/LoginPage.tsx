import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { confirmEnrollment, loadSession, startEnrollment, useAuthStore, verifyMfa, type Enrollment } from '@/store/auth'
import { Logo } from '@/assets/brand/Logo'
import { Button, Input } from '@/components/ui-login'

const DEMO_ACCOUNTS = [
  { username: 'admin', label: 'Admin (Administrator)' },
  { username: 'operator', label: 'Operator (Dispecer)' },
] as const

export default function LoginPage() {
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/app'
  const target = from === '/' ? '/app' : from

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  // Second factor for accounts that are not MFA-exempt (exempt demo accounts skip it).
  const [mfa, setMfa] = useState(false)
  const [code, setCode] = useState('')
  const [enrollmentNeeded, setEnrollmentNeeded] = useState(false)
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null)
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null)

  async function beginEnrollment() {
    setLoading(true)
    setError(null)
    try { setEnrollment(await startEnrollment()) }
    catch (err) { setError((err as Error).message || 'Nu s-a putut genera codul QR.') }
    finally { setLoading(false) }
  }

  function backToPassword() {
    setMfa(false)
    setEnrollmentNeeded(false)
    setEnrollment(null)
    setCode('')
    setPassword('')
    setError(null)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (recoveryCodes) {
      setLoading(true)
      try { await loadSession(); navigate(target, { replace: true }) }
      catch (err) { setError((err as Error).message) } finally { setLoading(false) }
      return
    }
    if (mfa) {
      if (!code.trim()) return setError('Introduceți codul de autentificare.')
      setLoading(true)
      try {
        if (enrollment) setRecoveryCodes(await confirmEnrollment(code))
        else { await verifyMfa(code); navigate(target, { replace: true }) }
      } catch (err) { setError((err as Error).message || 'Cod incorect.') } finally { setLoading(false) }
      return
    }
    if (!username.trim() || !password) return setError('Completați utilizatorul și parola.')
    setLoading(true)
    const res = await login(username, password, remember)
    if (res.ok && res.mfaRequired) {
      setMfa(true)
      if (res.enrollment) {
        setEnrollmentNeeded(true)
        await beginEnrollment()
      }
    } else if (res.ok) navigate(target, { replace: true })
    else setError(res.error || 'Utilizator sau parolă incorectă.')
    setLoading(false)
  }

  const fillDemo = (u: string) => {
    setUsername(u)
    setPassword('parola')
    setError(null)
  }

  return (
    <div className="h-screen w-full flex items-center justify-center bg-bg text-text p-4">
      <div className="w-[380px] bg-surface border border-[#2A2F34] rounded-[6px] p-6 flex flex-col gap-5 shadow-[0_8px_24px_rgba(0,0,0,0.4)]">
        {/* Logo and Title */}
        <div className="flex flex-col items-center text-center gap-2">
          <Logo size={28} />
          <h1 className="text-[18px] font-semibold text-text mt-1">
            Autentificare dispecerat
          </h1>
          <p className="text-[12px] text-[#9AA1A8]">
            Poliția Rutieră Iași · Sistem operativ
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-3.5">
          {!mfa && (
            <>
            <div className="flex flex-col gap-1">
              <label htmlFor="username" className="text-[12px] text-[#9AA1A8]">
                Utilizator
              </label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                autoFocus
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ex: operator"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="password" className="text-[12px] text-[#9AA1A8]">
                Parolă
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <label className="flex items-center gap-2 text-[12px] text-[#9AA1A8] cursor-pointer select-none">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="w-3.5 h-3.5 rounded-[2px] border-[#2A2F34] bg-surface-2 text-accent focus:ring-0 cursor-pointer"
              />
              <span>Ține-mă minte</span>
            </label>
            </>
          )}

          {mfa && enrollment && !recoveryCodes && (
            <div className="flex flex-col gap-2 text-[12px] text-[#9AA1A8]">
              <p>Prima autentificare: scanați codul QR cu o aplicație de autentificare (Google Authenticator, Microsoft Authenticator, Aegis), apoi introduceți codul de 6 cifre.</p>
              <img src={enrollment.qr_svg_data_uri} alt="Cod QR pentru aplicația de autentificare" className="mx-auto w-40 h-40 bg-white p-2 rounded-[4px]" />
              <p>Cheie manuală: <code data-testid="mfa-secret" className="select-all break-all text-text">{enrollment.secret}</code></p>
            </div>
          )}

          {recoveryCodes && (
            <div role="status" className="flex flex-col gap-2 text-[12px] text-[#9AA1A8]">
              <p className="font-medium text-text">Coduri de recuperare (afișate o singură dată). Păstrați-le în siguranță:</p>
              <ul className="grid grid-cols-2 gap-1 font-mono select-all">{recoveryCodes.map((c) => <li key={c}>{c}</li>)}</ul>
            </div>
          )}

          {mfa && !recoveryCodes && (!enrollmentNeeded || enrollment) && (
            <div className="flex flex-col gap-1">
              <label htmlFor="mfa-code" className="text-[12px] text-[#9AA1A8]">
                Cod de autentificare
              </label>
              <Input
                id="mfa-code"
                type="text"
                autoComplete="one-time-code"
                inputMode="numeric"
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="123456 sau cod de recuperare"
              />
            </div>
          )}

          {error && (
            <p role="alert" className="text-[12px] text-crit">
              {error}
            </p>
          )}

          {enrollmentNeeded && !enrollment && !loading ? (
            <Button
              type="button"
              variant="primary"
              onClick={() => void beginEnrollment()}
              className="w-full justify-center h-8 mt-1 font-medium text-[13px]"
            >
              Reîncearcă generarea codului QR
            </Button>
          ) : (
            <Button
              type="submit"
              variant="primary"
              disabled={loading}
              className="w-full justify-center h-8 mt-1 font-medium text-[13px]"
            >
              {loading ? 'Se verifică…' : recoveryCodes ? 'Am salvat codurile, continuă' : mfa ? 'Verifică' : 'Intră'}
            </Button>
          )}

          {mfa && !recoveryCodes && (
            <Button
              type="button"
              variant="ghost"
              disabled={loading}
              onClick={backToPassword}
              className="w-full justify-center h-7 text-[12px]"
            >
              Înapoi
            </Button>
          )}
        </form>

        {/* Demo Accounts as 2 Ghost Buttons */}
        {!mfa && <div className="pt-3 border-t border-[#2A2F34] flex flex-col gap-1.5">
          <span className="text-[11px] text-text-faint text-center">
            Conturi demo:
          </span>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <Button
                key={a.username}
                type="button"
                variant="ghost"
                onClick={() => fillDemo(a.username)}
                className="justify-center text-[12px] h-7 border border-[#2A2F34] bg-surface-2 hover:bg-surface text-[#9AA1A8] hover:text-text"
              >
                {a.username}
              </Button>
            ))}
          </div>
        </div>}

        {/* Discrete bottom legal text */}
        <div className="text-[11px] text-text-faint text-center pt-1">
          Acces auditat · Directiva UE 2016/680
        </div>
      </div>
    </div>
  )
}
