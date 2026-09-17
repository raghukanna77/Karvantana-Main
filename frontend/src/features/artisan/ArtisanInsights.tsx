/** Business insights + the KARVANTANA Assistant (tool-backed answers only). */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { inr, type ArtisanDashboard } from '../../core/types'
import { KBadge, KButton, KCard, KInput, KVStat } from '../../design'

interface AssistantResponse {
  answer: string
  tool: string
  data: Record<string, unknown>
}

const SUGGESTIONS = [
  'Which products are selling well?',
  'Show me my pending orders.',
  'What should I improve this week?',
  'How are my sales this month?',
]

export default function ArtisanInsights() {
  const [dash, setDash] = useState<ArtisanDashboard | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AssistantResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ArtisanDashboard>('/analytics/artisan/dashboard').then(setDash).catch(() => setDash(null))
  }, [])

  async function ask(q: string) {
    setBusy(true); setError(''); setAnswer(null)
    try {
      setAnswer(await api.post<AssistantResponse>('/ai/assistant/ask', { question: q }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The assistant is unavailable right now.')
    } finally { setBusy(false) }
  }

  return (
    <div className="k-stack">
      <h2 style={{ fontSize: 22 }}>📊 Insights</h2>

      {dash && (
        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
          <KCard><KVStat value={inr(dash.totals.revenue)} label="Total revenue" /></KCard>
          <KCard><KVStat value={dash.totals.orders} label="Orders" /></KCard>
          <KCard><KVStat value={dash.totals.unique_buyers} label="Buyers" /></KCard>
          <KCard><KVStat value={`${dash.totals.repeat_rate}%`} label="Repeat rate" /></KCard>
          <KCard><KVStat value={inr(dash.totals.avg_order_value)} label="Avg order" /></KCard>
        </div>
      )}

      {dash && dash.most_viewed.length > 0 && (
        <KCard>
          <div className="k-spread"><h3>👀 What buyers are looking at</h3><KBadge tone="violet">real views</KBadge></div>
          <div className="k-stack" style={{ marginTop: 8 }}>
            {dash.most_viewed.map((p) => (
              <div key={p.id} className="k-spread">
                <span>{p.title}</span><span className="muted small">{p.views} views</span>
              </div>
            ))}
          </div>
        </KCard>
      )}

      <KCard className="pad-lg">
        <div className="k-spread"><h3>💬 Ask KARVANTANA</h3><KBadge tone="blue">answers only from your data</KBadge></div>
        <p className="muted small">The assistant reads your real orders and products through restricted tools — it cannot invent numbers or touch your prices.</p>
        <div className="k-row" style={{ margin: '12px 0' }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} className="k-btn sm ghost" onClick={() => void ask(s)}>{s}</button>
          ))}
        </div>
        <div className="k-row">
          <KInput value={question} onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask about your business…" style={{ flex: 1, minWidth: 220 }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && question.trim()) void ask(question) }} />
          <KButton disabled={!question.trim() || busy} onClick={() => void ask(question)}>Ask</KButton>
        </div>
        {error && <div className="k-error" style={{ marginTop: 10 }}>{error}</div>}
        {answer && (
          <div className="k-ok" style={{ marginTop: 12 }} role="status">
            {answer.answer}
            <div className="muted small" style={{ marginTop: 6 }}>source: {answer.tool}</div>
          </div>
        )}
      </KCard>
    </div>
  )
}
