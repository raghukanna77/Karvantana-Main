/** Demo Mode — deterministic 19-step judge walkthrough on labeled demo data. */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KButton, KCard } from '../../design'
import { SihPage } from './shared'

interface Step { n: number; title: string; detail: string; to?: string; login?: string }

const STEPS: Step[] = [
  { n: 1, title: 'Login as artisan', detail: 'Use the demo artisan Priya — clearly labeled (DEMO) in the seed data.', to: '/login', login: 'artisan1@karvantana.demo / artisan-demo-1' },
  { n: 2, title: 'Capture / upload product photo', detail: 'Wizard accepts camera or gallery; AI quality checks run immediately (blur, lighting, resolution).', to: '/artisan/products/new' },
  { n: 3, title: 'Speak about the product (regional language)', detail: 'Tamil sample hints are one tap; browser speech recognition or typed transcript — both supported.', to: '/artisan/products/new' },
  { n: 4, title: 'Speech → text → translation', detail: 'Language detection, STT provider, craft-lexicon translation; original + translated stored side by side.', to: '/artisan/products/new' },
  { n: 5, title: 'Structured extraction with confidence', detail: 'Every field shows value + confidence % + source (VOICE/IMAGE/AI_INFERENCE); low confidence is flagged “confirm”, never silently accepted.', to: '/artisan/products/new' },
  { n: 6, title: 'AI catalogue generated', detail: 'Generated ONLY from structured fields — the model never sees raw transcripts, blocking hallucination at the source.', to: '/artisan/products/new' },
  { n: 7, title: 'Image quality report', detail: 'Quality score with pass/fail checks; enhancement is non-destructive (original always preserved).', to: '/artisan/products/new' },
  { n: 8, title: 'AI confidence / validation state', detail: 'Overall confidence is shown with per-field sources; the AI marks what it is unsure about.', to: '/artisan/products/new' },
  { n: 9, title: 'Artisan approves / edits / regenerates', detail: 'Approve, edit, reject or regenerate any field. Every decision is recorded in the ai_field_approvals audit trail — human-in-the-loop is provable, not claimed.', to: '/artisan/products/new' },
  { n: 10, title: 'Smart pricing recommendation', detail: 'Cost model + market band + demand signal; “Why this price?” opens the factor-by-factor explanation.', to: '/artisan/products/new' },
  { n: 11, title: 'Pricing explanation', detail: 'Artisan sees cost contribution, market range, margin scenarios. Accept, edit, or ignore — AI never sets prices.', to: '/artisan/products/new' },
  { n: 12, title: 'Publish product', detail: 'Nothing publishes without the artisan’s explicit approval — the platform’s core safety property.', to: '/artisan/products/new' },
  { n: 13, title: 'Buyer discovery (natural-language search)', detail: 'Sign in as the buyer in a second tab; search the marketplace and find the published product.', to: '/explore', login: 'anita@example.com / buyer-demo-1234' },
  { n: 14, title: 'Buyer views the artisan (not just the product)', detail: 'Product page leads with the maker: studio, craft, location, reputation, other works.', to: '/explore' },
  { n: 15, title: 'Buyer orders (idempotent, server-verified payment)', detail: 'Checkout creates the order; the demo gateway signs a webhook exactly like a real one; the server — never the client — confirms payment.', to: '/checkout/REPLACE_WITH_PRODUCT_ID' },
  { n: 16, title: 'Bulk / custom request (B2B)', detail: 'B2B portal: natural-language requirement → parsed → matched artisans with reasons → quote → accept reprices the order at the quoted unit price.', to: '/b2b', login: 'orders@brightspaces.example.com / buyer-demo-1234' },
  { n: 17, title: 'Buyer rates, follows, saves the artisan', detail: 'Reviews unlock only after real delivery; follows and saves power the relationship loop.', to: '/buyer/orders' },
  { n: 18, title: 'Direct reorder (one tap)', detail: '“Buy again from this artisan” re-creates the order idempotently — repeat commerce is a feature, not a hope.', to: '/buyer/orders' },
  { n: 19, title: 'Artisan sees it all (dashboard + AI insights)', detail: 'Back as Priya: real revenue, repeat rate, AI insights computed from actual rows — ask the assistant “Which products are selling well?”', to: '/artisan', login: 'artisan1@karvantana.demo / artisan-demo-1' },
]

export default function DemoModePage() {
  const [done, setDone] = useState<Set<number>>(new Set())
  const navigate = useNavigate()
  const toggle = (n: number) => {
    const next = new Set(done)
    if (next.has(n)) next.delete(n); else next.add(n)
    setDone(next)
  }

  return (
    <SihPage wide title="KARVANTANA — Guided Demo"
      subtitle="The complete core journey on clearly-labeled demo data. Every external dependency (AI, payments, logistics) has a labeled demo provider, so this flow never depends on a vendor being up.">
      <KCard className="pad-lg" style={{ marginTop: 14 }}>
        <div className="k-row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <span className="k-badge gold">DEMO DATA — labeled, deterministic, reseedable</span>
          <span className="k-badge green">works fully offline of external APIs</span>
          <span className="k-badge blue">progress: {done.size}/{STEPS.length}</span>
        </div>
        <div style={{ height: 6, background: 'var(--glass)', borderRadius: 3, overflow: 'hidden', marginTop: 12 }}>
          <div style={{ width: `${(done.size / STEPS.length) * 100}%`, height: '100%', background: 'linear-gradient(90deg, var(--blue), var(--violet))' }} />
        </div>
        <p className="muted small" style={{ marginTop: 10, marginBottom: 0 }}>
          If anything external fails live, the demo providers take over and the UI labels the data
          “Demo fallback data” — the flow never pretends a vendor responded.
        </p>
      </KCard>

      {STEPS.map((s) => (
        <KCard key={s.n} className="pad-lg" style={{ marginTop: 12, borderColor: done.has(s.n) ? 'rgba(47,179,124,0.35)' : undefined }}>
          <div className="k-spread">
            <div className="k-row" style={{ gap: 10 }}>
              <span style={{
                width: 30, height: 30, borderRadius: '50%', display: 'grid', placeItems: 'center',
                background: done.has(s.n) ? 'rgba(47,179,124,0.2)' : 'var(--glass)',
                border: `1px solid ${done.has(s.n) ? 'rgba(47,179,124,0.5)' : 'var(--stroke)'}`,
                fontWeight: 700, fontSize: 13,
              }}>{done.has(s.n) ? '✓' : s.n}</span>
              <strong>{s.title}</strong>
            </div>
            <span className="k-row" style={{ gap: 8 }}>
              {s.login && <span className="muted small">{s.login}</span>}
              {s.to && !s.to.includes('REPLACE') && (
                <KButton size="sm" onClick={() => {
                  toggle(s.n)
                  navigate(s.to!)
                }}>{done.has(s.n) ? 'Reopen' : 'Open →'}</KButton>
              )}
            </span>
          </div>
          <p className="muted small" style={{ margin: '8px 0 0 40px' }}>{s.detail}</p>
        </KCard>
      ))}
    </SihPage>
  )
}
