/** Design system components (KButton, KCard, KInput, badges, states). */
import { type ReactNode } from 'react'
import { LANGUAGES, persistLanguage, useT, type Lang } from '../i18n'

/** Global language switcher — 10 languages, persists locally + server-side. */
export function KLangSwitcher({ compact }: { compact?: boolean }) {
  const { lang } = useT()
  return (
    <select
      className="k-select"
      style={{ width: 'auto', padding: '6px 10px', fontSize: 13 }}
      aria-label="Language / భాష / भाषा"
      value={lang}
      onChange={(e) => {
        const next = e.target.value as Lang
        persistLanguage(next)
        useUiSetLang(next)
      }}
    >
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>{compact ? l.code.toUpperCase() : l.nativeName}</option>
      ))}
    </select>
  )
}

// setLang lives in the stores module; imported lazily to avoid a cycle.
import { useUi as useUiStore } from '../state/stores'
function useUiSetLang(l: Lang) {
  useUiStore.getState().setLang(l)
}

export function KButton({
  children, variant = 'primary', size, block, onClick, type = 'button', disabled, title, style,
}: {
  children: ReactNode
  variant?: 'primary' | 'ghost' | 'gold' | 'danger'
  size?: 'sm' | 'lg'
  block?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  title?: string
  style?: React.CSSProperties
}) {
  const cls = ['k-btn', variant, size, block ? 'block' : ''].filter(Boolean).join(' ')
  return (
    <button className={cls} onClick={onClick} type={type} disabled={disabled} title={title} style={style}>
      {children}
    </button>
  )
}

export function KCard({ children, className = '', style }: { children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return <div className={`k-card ${className}`} style={style}>{children}</div>
}

export function KInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className="k-input" {...props} />
}

export function KTextarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className="k-textarea" {...props} />
}

export function KSelect(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className="k-select" {...props} />
}

export function KLabel({ children }: { children: ReactNode }) {
  return <label className="k-label">{children}</label>
}

export function KBadge({ children, tone }: { children: ReactNode; tone?: 'blue' | 'violet' | 'green' | 'gold' | 'red' }) {
  return <span className={`k-badge ${tone ?? ''}`}>{children}</span>
}

export function KConfidence({ score, label }: { score: number; label?: string }) {
  const pct = Math.round(score * 100)
  const caption = label ?? (pct >= 75 ? 'AI confidence' : 'Please confirm')
  return (
    <div className="k-confidence" title={`${caption}: ${pct}%`}>
      <div className="k-confidence-bar"><div className="k-confidence-fill" style={{ width: `${pct}%` }} /></div>
      <div className="k-confidence-label">{caption} {pct}%</div>
    </div>
  )
}

export function KEmpty({ icon, title, hint, action }: { icon: string; title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="k-empty">
      <div className="big" aria-hidden>{icon}</div>
      <div style={{ fontWeight: 700, fontSize: 17, marginBottom: 4 }}>{title}</div>
      {hint && <div className="small">{hint}</div>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}

export function KError({ message }: { message: string }) {
  return <div className="k-error" role="alert">{message}</div>
}

export function KObservable({ children }: { children: ReactNode }) {
  return <div className="k-ok">{children}</div>
}

export function KSkeleton({ h = 90 }: { h?: number }) {
  return <div className="k-skeleton" style={{ height: h }} />
}

/** AI processing stages — real stages, no fake percentages. */
export function KAIStages({ stages }: { stages: { label: string; state: 'done' | 'active' | 'pending' }[] }) {
  return (
    <div className="k-stages" aria-live="polite">
      {stages.map((s) => (
        <div key={s.label} className={`k-stage ${s.state}`}>
          <span className="dot">{s.state === 'done' ? '✓' : s.state === 'active' ? '●' : '○'}</span>
          {s.label}
        </div>
      ))}
    </div>
  )
}

export function KVStat({ value, label }: { value: ReactNode; label: string }) {
  return (
    <div className="k-stat">
      <span className="v">{value}</span>
      <span className="l">{label}</span>
    </div>
  )
}
