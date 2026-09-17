/** Ask KARVANTANA — the AI business assistant. Answers come from real tools
 *  (orders, products, demand) — sources are shown; nothing is invented. */

import { useEffect, useRef, useState } from 'react'
import { api } from '../../core/api'
import { KAIStages, KBadge, KButton, KCard, KError, KInput } from '../../design'

interface Exchange {
  q: string
  answer: string | null
  data?: unknown
  sources?: string[]
  pending?: boolean
}

const SUGGESTIONS = [
  'Which products are selling well?',
  'Show me my pending orders',
  'Which products need better photos?',
  'What should I improve this week?',
]

export default function AssistantPage() {
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [question, setQuestion] = useState('')
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [exchanges])

  async function ask(q: string) {
    if (!q.trim()) return
    setError('')
    setExchanges((x) => [...x, { q, answer: null, pending: true }])
    setQuestion('')
    try {
      const res = await api.post<{ answer: string; data: unknown; sources: string[] }>('/ai/assistant/ask', { question: q })
      setExchanges((x) => x.map((e) => (e.q === q && e.pending ? { ...e, answer: res.answer, data: res.data, sources: res.sources, pending: false } : e)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The assistant is unavailable right now.')
      setExchanges((x) => x.filter((ex) => !(ex.q === q && ex.pending)))
    }
  }

  return (
    <div className="container" style={{ padding: '20px 16px 110px', maxWidth: 680 }}>
      <div className="k-stack">
        <div>
          <h2 style={{ fontSize: 22 }}>Ask KARVANTANA</h2>
          <div className="muted small">Your business assistant — every answer comes from your real shop data.</div>
        </div>

        {exchanges.map((e, i) => (
          <div key={i} className="k-stack" style={{ gap: 8 }}>
            <KCard className="k-weave" style={{ alignSelf: 'flex-end', maxWidth: '85%', padding: '12px 16px' }}>
              <span style={{ fontSize: 14.5 }}>{e.q}</span>
            </KCard>
            {e.pending && (
              <KCard style={{ maxWidth: '92%' }}>
                <KAIStages stages={[
                  { label: 'Understanding your question', state: 'done' },
                  { label: 'Checking your shop data', state: 'active' },
                  { label: 'Preparing your answer', state: 'pending' },
                ]} />
              </KCard>
            )}
            {!e.pending && e.answer && (
              <KCard style={{ maxWidth: '92%' }}>
                <div style={{ fontSize: 14.5, whiteSpace: 'pre-wrap' }}>{e.answer}</div>
                {e.sources && e.sources.length > 0 && (
                  <div className="muted small" style={{ marginTop: 8 }}>
                    Sources: {e.sources.map((s) => <KBadge key={s} tone="violet">{s.replace('tool:', '')}</KBadge>)}
                  </div>
                )}
              </KCard>
            )}
          </div>
        ))}

        {error && <KError message={error} />}

        {exchanges.length === 0 && (
          <KCard className="k-weave">
            <h3>What's on your mind?</h3>
            <div className="k-stack" style={{ marginTop: 10, gap: 8 }}>
              {SUGGESTIONS.map((s) => (
                <KButton key={s} variant="ghost" size="sm" onClick={() => void ask(s)}>{s}</KButton>
              ))}
            </div>
          </KCard>
        )}

        <div className="k-row" style={{ position: 'sticky', bottom: 86 }}>
          <KInput style={{ flex: 1 }} value={question} onChange={(ev) => setQuestion(ev.target.value)}
                  onKeyDown={(ev) => { if (ev.key === 'Enter') void ask(question) }}
                  placeholder="Ask about sales, orders, pricing…" aria-label="Ask the assistant" />
          <KButton onClick={() => void ask(question)} disabled={!question.trim()}>Ask</KButton>
        </div>
        <div ref={endRef} />
      </div>
    </div>
  )
}
