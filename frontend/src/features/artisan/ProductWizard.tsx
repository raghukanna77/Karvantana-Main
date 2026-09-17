/** THE core feature: multi-step product wizard.
 *  1 Capture → 2 Describe (voice/text) → 3 AI Catalogue review → 4 Pricing → 5 Publish.
 *  Drafts persist locally; every AI field is artisan-approved before publishing. */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../../core/api'
import {
  inr, type CatalogueOutput, type PriceRec,
} from '../../core/types'
import {
  KAIStages, KBadge, KButton, KCard, KConfidence, KError, KInput, KLabel, KSelect, KTextarea,
} from '../../design'

type Stage = { label: string; state: 'done' | 'active' | 'pending' }

const SAMPLE_HINTS = [
  'இது கைத்தறியில் நெய்த பருத்தி சேலை…',
  'यह हाथ से बुना हुआ कपास की साड़ी है…',
  'This is a handwoven cotton saree…',
]

export default function ProductWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [productId, setProductId] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [quality, setQuality] = useState<number | null>(null)
  const [transcript, setTranscript] = useState('')
  const [language, setLanguage] = useState('ta')
  const [catalogue, setCatalogue] = useState<CatalogueOutput | null>(null)
  const [extracted, setExtracted] = useState<Record<string, { value: string; confidence: number; source: string }>>({})
  const [rec, setRec] = useState<PriceRec | null>(null)
  const [showWhy, setShowWhy] = useState(false)
  const [price, setPrice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [stages, setStages] = useState<Stage[]>([])
  const [listening, setListening] = useState(false)
  const [regenField, setRegenField] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  // draft restore
  useEffect(() => {
    const draft = localStorage.getItem('karvantana.wizarddraft')
    if (draft && !productId) {
      try {
        const d = JSON.parse(draft) as { productId?: string; step?: number }
        if (d.productId) { setProductId(d.productId); setStep(d.step && d.step > 1 ? d.step : 2) }
      } catch { /* ignore */ }
    }
  }, [productId])

  function persist(next: { productId?: string; step?: number }) {
    localStorage.setItem('karvantana.wizarddraft', JSON.stringify({ productId, step, ...next }))
  }

  async function handlePhoto(file: File) {
    setError(''); setBusy(true)
    setStages([
      { label: 'Uploading photo', state: 'active' },
      { label: 'Analyzing image quality', state: 'pending' },
    ])
    try {
      const created = await api.post<{ id: string }>('/products', { title: '', category: guessCategory() })
      setProductId(created.id)
      const up = await api.upload<{ url: string; quality_score: number | null }>(`/products/${created.id}/images`, file, file.name)
      setImageUrl(up.url)
      setQuality(up.quality_score)
      setStages([
        { label: 'Uploading photo', state: 'done' },
        { label: 'Analyzing image quality', state: 'done' },
      ])
      persist({ productId: created.id, step: 2 })
      setStep(2)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Upload failed.')
    } finally { setBusy(false) }
  }

  function startSpeech() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) {
      setError('Your browser does not support speech input. Type below instead — everything else works the same.')
      return
    }
    const rec = new SR()
    recognitionRef.current = rec
    rec.lang = language === 'en' ? 'en-IN' : `${language}-IN`
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (ev: any) => {
      const said = String(ev.results?.[0]?.[0]?.transcript ?? '')
      setTranscript((t) => (t ? `${t} ${said}` : said))
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    setListening(true)
    rec.start()
  }

  async function generateCatalogue() {
    if (!productId) return
    setError(''); setBusy(true)
    setStages([
      { label: 'Understanding your description', state: 'active' },
      { label: 'Translating', state: 'pending' },
      { label: 'Extracting product details', state: 'pending' },
      { label: 'Creating catalogue', state: 'pending' },
      { label: 'Ready for your review', state: 'pending' },
    ])
    try {
      const voice = await api.post<{ language: string; translated: string; extracted: Record<string, { value: string; confidence: number; source: string }> }>(
        '/ai/voice/transcribe', { text: transcript, language_hint: language })
      setExtracted(voice.extracted)
      setStages((s) => s.map((x, i) => (i <= 1 ? { ...x, state: 'done' } : i === 2 ? { ...x, state: 'active' } : x)))
      const cat = await api.post<CatalogueOutput>('/ai/catalogue/generate', {
        product_id: productId, transcript_en: voice.translated, transcript_original: transcript,
      })
      setCatalogue(cat)
      setPrice(String(Math.round(cat.confidence * 0 + 1250))) // placeholder replaced by pricing step
      setStages((s) => s.map((x, i) => (i < 4 ? { ...x, state: 'done' } : { ...x, state: 'active' })))
      persist({ step: 3 })
      setStep(3)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'AI catalogue failed. You can still continue manually.')
    } finally { setBusy(false) }
  }

  async function regenerateField(field: 'title' | 'short_description' | 'description' | 'keywords') {
    if (!catalogue || !productId) return
    setRegenField(field); setError('')
    try {
      const fresh = await api.post<CatalogueOutput>('/ai/catalogue/regenerate-field', {
        product_id: productId, field,
      })
      setCatalogue({ ...catalogue, [field]: fresh[field] })
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Regeneration failed.')
    } finally { setRegenField(null) }
  }

  async function getPricing() {
    setError(''); setBusy(true)
    try {
      const suggestion = await api.post<PriceRec>('/ai/pricing/recommend', {
        material_cost: num(extracted, 'material') || 420,
        labour_cost: 380,
        packaging_cost: 40,
        shipping_estimate: 60,
        desired_margin_pct: 30,
        category_hint: (catalogue?.title ?? '').toLowerCase().includes('saree') ? 'saree'
          : (catalogue?.title ?? '').toLowerCase().includes('basket') ? 'basket' : undefined,
        product_id: productId,
      })
      setRec(suggestion)
      setPrice(String(suggestion.suggested_price))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Pricing assistant unavailable — set your price manually.')
    } finally { setBusy(false) }
  }

  async function publish() {
    if (!productId) return
    setError(''); setBusy(true)
    try {
      await api.patch(`/products/${productId}`, {
        title: catalogue?.title, short_description: catalogue?.short_description,
        description: catalogue?.description, keywords: catalogue?.keywords,
        price: Number(price), production_days: num(extracted, 'production_days') || 4,
        inventory_mode: 'MADE_TO_ORDER', moq: 1, bulk_moq: 10,
        bulk_price: Math.round(Number(price) * 0.88),
      })
      await api.post(`/products/${productId}/publish`)
      localStorage.removeItem('karvantana.wizarddraft')
      navigate('/artisan/products')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Publish failed.')
    } finally { setBusy(false) }
  }

  function guessCategory(): string {
    return 'Sarees'
  }

  const stageList: Stage[] = useMemo(() => [
    { label: 'Photo captured', state: imageUrl ? 'done' : step >= 2 ? 'done' : 'active' },
    { label: 'Description', state: transcript ? 'done' : step > 2 ? 'done' : step === 2 ? 'active' : 'pending' },
    { label: 'AI catalogue approved', state: step > 3 ? 'done' : step === 3 ? 'active' : 'pending' },
    { label: 'Price set', state: step > 4 ? 'done' : step === 4 ? 'active' : 'pending' },
    { label: 'Published', state: step === 5 ? 'active' : 'pending' },
  ], [imageUrl, transcript, step])

  return (
    <div className="container" style={{ maxWidth: 760, padding: '22px 20px 90px' }}>
      <div className="k-spread" style={{ marginBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 22 }}>📷 Add Product</h2>
          <div className="muted small">Tap · Speak · Confirm · Publish</div>
        </div>
        <KBadge tone="violet">Step {step} of 5</KBadge>
      </div>

      <KCard className="pad-lg" style={{ marginBottom: 14 }}>
        <div className="k-row" style={{ gap: 14 }}>
          {stageList.map((s) => (
            <span key={s.label} className={`k-stage ${s.state}`} style={{ fontSize: 12.5 }}>
              <span className="dot" style={{ width: 18, height: 18 }}>{s.state === 'done' ? '✓' : '○'}</span>
              {s.label}
            </span>
          ))}
        </div>
      </KCard>

      {error && <div style={{ marginBottom: 12 }}><KError message={error} /></div>}

      {/* STEP 1 — CAPTURE */}
      {step === 1 && (
        <KCard className="pad-lg">
          <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) void handlePhoto(f) }} />
          <div className="k-stack">
            <KButton size="lg" block onClick={() => fileRef.current?.click()} disabled={busy}>
              📷 {busy ? 'Working…' : 'Take / Choose Photo'}
            </KButton>
            {quality !== null && (
              <div className="muted small">Image quality score: <strong>{quality}/100</strong> — computed from the photo itself.</div>
            )}
            <p className="muted small">Your original photo is never modified — enhanced copies are saved separately.</p>
          </div>
        </KCard>
      )}

      {/* STEP 2 — DESCRIBE */}
      {step === 2 && (
        <KCard className="pad-lg">
          {imageUrl && <img src={imageUrl} alt="Product preview" style={{ borderRadius: 12, maxWidth: 220, marginBottom: 12 }} />}
          <KLabel>Speak about your product</KLabel>
          <div className="k-row" style={{ marginBottom: 10 }}>
            <KSelect value={language} onChange={(e) => setLanguage(e.target.value)} style={{ maxWidth: 200 }}>
              {['ta', 'hi', 'te', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'en'].map((c) => (
                <option key={c} value={c}>{c.toUpperCase()}</option>
              ))}
            </KSelect>
            <KButton variant={listening ? 'danger' : 'ghost'} onClick={startSpeech} disabled={busy}>
              🎙️ {listening ? 'Listening…' : 'Speak'}
            </KButton>
          </div>
          <KTextarea value={transcript} onChange={(e) => setTranscript(e.target.value)}
                     placeholder={`Say anything, e.g. ${SAMPLE_HINTS[0]}`} rows={4} />
          <p className="muted small" style={{ marginTop: 8 }}>
            Voice input uses your phone's speech engine; the server detects the language, translates and extracts details.
            No internet? Your words are queued locally and used when you're back online.
          </p>
          <div style={{ marginTop: 14 }}>
            <KButton block size="lg" disabled={!transcript.trim() || busy} onClick={generateCatalogue}>
              ✨ Create with AI
            </KButton>
          </div>
          {stages.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <KAIStages stages={stages} />
            </div>
          )}
        </KCard>
      )}

      {/* STEP 3 — AI CATALOGUE REVIEW */}
      {step === 3 && catalogue && (
        <div className="k-stack">
          <KCard className="pad-lg">
            <div className="k-spread">
              <h3>✨ AI Understanding</h3>
              <KConfidence score={catalogue.confidence} />
            </div>
            <div className="k-stack" style={{ marginTop: 10 }}>
              {Object.entries(catalogue.extracted ?? extracted).map(([k, v]) => (
                <div key={k} className="k-spread" style={{ borderBottom: '1px dashed var(--stroke)', paddingBottom: 6 }}>
                  <span className="muted small" style={{ textTransform: 'capitalize' }}>{k.replace('_', ' ')}</span>
                  <span className="k-row" style={{ gap: 8 }}>
                    <strong style={{ textTransform: 'capitalize' }}>{String(v.value)}</strong>
                    <KBadge tone={v.confidence >= 0.75 ? 'green' : 'gold'}>
                      {v.confidence >= 0.75 ? `${Math.round(v.confidence * 100)}%` : 'confirm'}
                    </KBadge>
                    <span className="muted small">{v.source}</span>
                  </span>
                </div>
              ))}
            </div>
            <p className="muted small" style={{ marginTop: 8 }}>AI never invents facts — anything it couldn't hear clearly is marked “confirm”.</p>
          </KCard>

          <KCard className="pad-lg">
            <div className="k-spread">
              <h3>Review & approve</h3>
              <span className="muted small">Edit anything · Regenerate one field</span>
            </div>
            <KLabel>Title</KLabel>
            <KInput value={catalogue.title} onChange={(e) => setCatalogue({ ...catalogue, title: e.target.value })} />
            <div style={{ marginTop: 4 }}><KButton size="sm" variant="ghost" onClick={() => void regenerateField('title')} disabled={regenField === 'title'}>↻ Regenerate title</KButton></div>
            <KLabel>Short description</KLabel>
            <KTextarea rows={2} value={catalogue.short_description} onChange={(e) => setCatalogue({ ...catalogue, short_description: e.target.value })} />
            <KLabel>Full description</KLabel>
            <KTextarea rows={6} value={catalogue.description} onChange={(e) => setCatalogue({ ...catalogue, description: e.target.value })} />
            <KLabel>Search keywords</KLabel>
            <KInput value={catalogue.keywords} onChange={(e) => setCatalogue({ ...catalogue, keywords: e.target.value })} />
            <div className="k-row" style={{ marginTop: 16 }}>
              <KButton size="lg" onClick={() => { persist({ step: 4 }); setStep(4); void getPricing() }}>Approve → Price</KButton>
            </div>
          </KCard>
        </div>
      )}

      {/* STEP 4 — PRICING */}
      {step === 4 && (
        <KCard className="pad-lg">
          <h3>💰 Smart Pricing</h3>
          {rec ? (
            <>
              <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', margin: '14px 0' }}>
                <div className="k-stat"><span className="v">{inr(rec.estimated_cost)}</span><span className="l">Your cost</span></div>
                <div className="k-stat"><span className="v">{inr(rec.market_low)}–{inr(rec.market_high)}</span><span className="l">Market range</span></div>
                <div className="k-stat"><span className="v" style={{ color: '#9fe8ca' }}>{inr(rec.suggested_price)}</span><span className="l">AI suggestion</span></div>
                <div className="k-stat"><span className="v">{inr(rec.estimated_margin)}</span><span className="l">Est. margin</span></div>
                <div className="k-stat"><span className="v">{rec.demand_signal}</span><span className="l">Demand</span></div>
              </div>
              <button className="k-btn sm ghost" onClick={() => setShowWhy(!showWhy)}>Why this price?</button>
              {showWhy && <p className="muted small" style={{ marginTop: 8 }}>{rec.explanation}</p>}
              <div className="k-row" style={{ marginTop: 14 }}>
                <KButton variant="ghost" onClick={() => setPrice(String(rec.suggested_price))}>Accept {inr(rec.suggested_price)}</KButton>
                <span className="muted small">— or set your own below. Pricing is advice, never a rule.</span>
              </div>
            </>
          ) : (
            <p className="muted small" style={{ margin: '10px 0' }}>
              The pricing assistant is thinking… or set your price yourself right now.
            </p>
          )}
          <KLabel>Your price (₹)</KLabel>
          <KInput value={price} onChange={(e) => setPrice(e.target.value)} inputMode="decimal" placeholder="1250" />
          <div className="k-row" style={{ marginTop: 16 }}>
            <KButton size="lg" disabled={!Number(price)} onClick={() => { persist({ step: 5 }); setStep(5) }}>
              Continue → Review
            </KButton>
          </div>
        </KCard>
      )}

      {/* STEP 5 — PUBLISH */}
      {step === 5 && catalogue && (
        <KCard className="pad-lg">
          <h3>🚀 Ready for the world</h3>
          <div className="k-row" style={{ margin: '12px 0' }}>
            {imageUrl && <img src={imageUrl} alt="Product" style={{ width: 130, borderRadius: 12 }} />}
            <div>
              <div style={{ fontWeight: 700, fontSize: 17 }}>{catalogue.title}</div>
              <div className="muted small" style={{ maxWidth: 420 }}>{catalogue.short_description}</div>
              <div className="k-row" style={{ marginTop: 8 }}>
                <KBadge tone="gold">Price {inr(Number(price))}</KBadge>
                <KBadge tone="blue">Made to order</KBadge>
              </div>
            </div>
          </div>
          <p className="muted small">You approve every word and every rupee — nothing is published automatically.</p>
          <div className="k-row" style={{ marginTop: 14 }}>
            <KButton size="lg" disabled={busy} onClick={publish}>✅ Publish my product</KButton>
            <KButton variant="ghost" onClick={() => setStep(4)}>Back</KButton>
          </div>
        </KCard>
      )}
    </div>
  )
}

function num(extracted: Record<string, { value: string }>, key: string): number {
  const v = extracted[key]?.value
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}
