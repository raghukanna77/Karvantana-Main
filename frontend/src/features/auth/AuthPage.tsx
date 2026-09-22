/** Auth: mobile OTP sign-in (artisan-friendly) + email accounts. Fully i18n. */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, apiOrigin } from '../../core/api'
import type { User } from '../../core/types'
import { KButton, KCard, KError, KInput, KLabel } from '../../design'
import { useAuth } from '../../state/stores'
import { homeFor } from '../../routing'
import { useT } from '../../i18n'

interface TokenPair {
  access_token: string
  refresh_token: string
  user: User
}

export default function AuthPage() {
  const [mode, setMode] = useState<'otp' | 'register' | 'login'>('otp')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [sentCode, setSentCode] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<'ARTISAN' | 'BUYER' | 'B2B_BUYER'>('ARTISAN')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [server, setServer] = useState(apiOrigin())
  const [serverSaved, setServerSaved] = useState(false)
  const setSession = useAuth((s) => s.setSession)
  const navigate = useNavigate()
  const { t } = useT()

  function done(tokens: TokenPair) {
    setSession(tokens.user, tokens.access_token)
    navigate(homeFor(tokens.user.role), { replace: true })
  }

  async function sendOtp() {
    setError(''); setBusy(true)
    try {
      const res = await api.post<{ demo_code: string | null; sent: boolean }>('/auth/otp/request', { phone })
      setSentCode(res.demo_code)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send the code.')
    } finally { setBusy(false) }
  }

  async function verifyOtp() {
    setError(''); setBusy(true)
    try {
      const tokens = await api.post<TokenPair>('/auth/otp/verify', { phone, code, full_name: name || undefined })
      done(tokens)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Verification failed.')
    } finally { setBusy(false) }
  }

  async function register() {
    setError(''); setBusy(true)
    try {
      done(await api.post<TokenPair>('/auth/register', { full_name: name, email, password, role }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create the account.')
    } finally { setBusy(false) }
  }

  async function login() {
    setError(''); setBusy(true)
    try {
      done(await api.post<TokenPair>('/auth/login', { email, password }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not sign in.')
    } finally { setBusy(false) }
  }

  function saveServer() {
    const v = server.trim().replace(/\/+$/, '')
    try {
      if (v) localStorage.setItem('karvantana.server', v)
      else localStorage.removeItem('karvantana.server')
    } catch { /* private mode */ }
    setServerSaved(true)
    window.setTimeout(() => setServerSaved(false), 1800)
  }

  return (
    <div className="container" style={{ maxWidth: 460, padding: '48px 20px' }}>
      <KCard className="pad-lg">
        <div style={{ textAlign: 'center', marginBottom: 18 }}>
          <div style={{ fontWeight: 850, fontSize: 22, letterSpacing: '0.12em' }}>KARVANTANA</div>
          <div className="muted small">{t('app.tagline')}</div>
        </div>

        <div className="k-row" style={{ marginBottom: 6 }}>
          {(['otp', 'register', 'login'] as const).map((m) => (
            <button
              key={m}
              className={`k-btn sm ${mode === m ? 'primary' : 'ghost'}`}
              onClick={() => { setMode(m); setError('') }}
            >
              {m === 'otp' ? t('auth.mobile_otp') : m === 'register' ? t('auth.create_account') : t('auth.sign_in')}
            </button>
          ))}
        </div>
        {error && <div style={{ margin: '10px 0' }}><KError message={error} /></div>}

        {mode === 'otp' && (
          <>
            <KLabel>{t('auth.your_mobile')}</KLabel>
            <KInput value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 98765 43210" inputMode="tel" />
            {sentCode ? (
              <>
                <KLabel>{t('auth.enter_code')} {sentCode && <span className="muted small">({t('auth.otp_demo_hint')}: {sentCode})</span>}</KLabel>
                <KInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="••••••" inputMode="numeric" />
                {name === '' && (
                  <>
                    <KLabel>{t('auth.name_new')}</KLabel>
                    <KInput value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Priya" />
                  </>
                )}
                <div style={{ marginTop: 16 }}><KButton block onClick={verifyOtp} disabled={busy || code.length < 4}>{t('auth.verify')}</KButton></div>
              </>
            ) : (
              <div style={{ marginTop: 16 }}><KButton block onClick={sendOtp} disabled={busy || phone.length < 8}>{t('auth.send_code')}</KButton></div>
            )}
            <p className="muted small" style={{ marginTop: 12 }}>{t('auth.new_here')}</p>
          </>
        )}

        {mode === 'register' && (
          <>
            <KLabel>{t('auth.i_am')}</KLabel>
            <div className="k-row">
              {([['ARTISAN', t('auth.role_artisan')], ['BUYER', t('auth.role_buyer')], ['B2B_BUYER', t('auth.role_b2b')]] as const).map(([r, label]) => (
                <button key={r} className={`k-btn sm ${role === r ? 'primary' : 'ghost'}`} onClick={() => setRole(r)}>{label}</button>
              ))}
            </div>
            <KLabel>{t('auth.full_name')}</KLabel>
            <KInput value={name} onChange={(e) => setName(e.target.value)} />
            <KLabel>{t('auth.email')}</KLabel>
            <KInput value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
            <KLabel>{t('auth.pw_hint')}</KLabel>
            <KInput value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
            <div style={{ marginTop: 16 }}><KButton block onClick={register} disabled={busy || !name || !email || password.length < 8}>{t('auth.create_account')}</KButton></div>
          </>
        )}

        {mode === 'login' && (
          <>
            <KLabel>{t('auth.email')}</KLabel>
            <KInput value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
            <KLabel>{t('auth.password')}</KLabel>
            <KInput value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
            <div style={{ marginTop: 16 }}><KButton block onClick={login} disabled={busy || !email || !password}>{t('auth.sign_in')}</KButton></div>
          </>
        )}

        <hr className="k-divider" />
        <KLabel>{t('auth.server_title')}</KLabel>
        <div className="k-row">
          <KInput value={server} onChange={(e) => setServer(e.target.value)} placeholder="http://192.168.1.20:8014" inputMode="url" />
          <KButton size="sm" onClick={saveServer}>{serverSaved ? '✓' : t('auth.server_save')}</KButton>
        </div>
        <p className="muted small" style={{ marginTop: 6 }}>{t('auth.server_hint')}</p>

        <hr className="k-divider" />
        <div className="muted small">
          <strong>{t('auth.demo_accounts')}</strong> ({t('auth.demo_sub')}):<br />
          🎨 artisan1@karvantana.demo / artisan-demo-1<br />
          🛍️ anita@example.com / buyer-demo-1234<br />
          🏢 orders@brightspaces.example.com / buyer-demo-1234<br />
          🛡️ admin@karvantana.demo / admin-demo-1234
        </div>
      </KCard>
    </div>
  )
}
