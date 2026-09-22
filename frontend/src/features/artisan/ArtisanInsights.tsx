/** Business insights + the KARVANTANA Assistant (tool-backed answers only). */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { inr, type ArtisanDashboard } from '../../core/types'
import { KBadge, KButton, KCard, KInput, KVStat } from '../../design'
import { useT } from '../../i18n'

interface AssistantResponse {
  answer: string
  tool: string
  data: Record<string, unknown>
}

export default function ArtisanInsights() {
  const { t } = useT()
  const SUGGESTIONS = [
    t('ins.q_selling'), t('ins.q_pending'), t('ins.q_improve'), t('ins.q_sales_month'),
  ]
  const [dash, setDash] = useState<ArtisanDashboard | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AssistantResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ArtisanDashboard>('/analytics/artisan/dashboard').then(setDash).catch(() => setDash(null))
  }, [t])

  async function ask(q: string) {
    setBusy(true); setError(''); setAnswer(null)
    try {
      setAnswer(await api.post<AssistantResponse>('/ai/assistant/ask', { question: q }))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('assistant.unavailable'))
    } finally { setBusy(false) }
  }

  return (
    <div className="k-stack">
      <h2 style={{ fontSize: 22 }}>📊 {t('nav.insights')}</h2>

      {dash && (
        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
          <KCard><KVStat value={inr(dash.totals.revenue)} label={t('ins.total_revenue')} /></KCard>
          <KCard><KVStat value={dash.totals.orders} label={t('nav.orders')} /></KCard>
          <KCard><KVStat value={dash.totals.unique_buyers} label={t('ins.buyers')} /></KCard>
          <KCard><KVStat value={`${dash.totals.repeat_rate}%`} label={t('ins.repeat_rate')} /></KCard>
          <KCard><KVStat value={inr(dash.totals.avg_order_value)} label={t('ins.avg_order')} /></KCard>
        </div>
      )}

      {dash && dash.most_viewed.length > 0 && (
        <KCard>
          <div className="k-spread"><h3>👀 {t('ins.most_viewed')}</h3><KBadge tone="violet">{t('ins.real_views')}</KBadge></div>
          <div className="k-stack" style={{ marginTop: 8 }}>
            {dash.most_viewed.map((p) => (
              <div key={p.id} className="k-spread">
                <span>{p.title}</span><span className="muted small">{p.views} {t('ins.views')}</span>
              </div>
            ))}
          </div>
        </KCard>
      )}

      <KCard className="pad-lg">
        <div className="k-spread"><h3>💬 {t('ins.ask')}</h3><KBadge tone="blue">{t('ins.only_your_data')}</KBadge></div>
        <p className="muted small">{t('ins.assistant_note')}</p>
        <div className="k-row" style={{ margin: '12px 0' }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} className="k-btn sm ghost" onClick={() => void ask(s)}>{s}</button>
          ))}
        </div>
        <div className="k-row">
          <KInput value={question} onChange={(e) => setQuestion(e.target.value)}
                  placeholder={t('ins.placeholder')} style={{ flex: 1, minWidth: 220 }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && question.trim()) void ask(question) }} />
          <KButton disabled={!question.trim() || busy} onClick={() => void ask(question)}>{t('ins.ask_btn')}</KButton>
        </div>
        {error && <div className="k-error" style={{ marginTop: 10 }}>{error}</div>}
        {answer && (
          <div className="k-ok" style={{ marginTop: 12 }} role="status">
            {answer.answer}
            <div className="muted small" style={{ marginTop: 6 }}>{t('ins.source')}: {answer.tool}</div>
          </div>
        )}
      </KCard>
    </div>
  )
}
