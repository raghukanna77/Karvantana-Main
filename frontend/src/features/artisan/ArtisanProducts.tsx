/** Artisan product catalogue with lifecycle management. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type ProductSummary } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty } from '../../design'

const LIFECYCLE_TONE: Record<string, 'green' | 'blue' | 'gold' | 'red' | undefined> = {
  PUBLISHED: 'green', DRAFT: 'gold', REVIEW_REQUIRED: 'blue', PAUSED: undefined, OUT_OF_STOCK: 'red', ARCHIVED: 'red',
}

export default function ArtisanProducts() {
  const [items, setItems] = useState<ProductSummary[] | null>(null)

  async function load() {
    const res = await api.get<{ items: ProductSummary[] }>('/products/mine')
    setItems(res.items)
  }
  useEffect(() => { void load() }, [])

  async function publish(id: string) {
    await api.post(`/products/${id}/publish`)
    void load()
  }
  async function unpause(id: string) {
    await api.patch(`/products/${id}`, { lifecycle: 'PAUSED' })
    void load()
  }

  return (
    <div className="k-stack">
      <div className="k-spread">
        <h2 style={{ fontSize: 22 }}>🧺 My Products</h2>
        <Link to="/artisan/products/new" className="k-btn primary sm">+ Add Product</Link>
      </div>

      {!items && <KCard><div className="k-skeleton" style={{ height: 160 }} /></KCard>}

      {items && items.length === 0 && (
        <KCard>
          <KEmpty icon="📷" title="No products yet"
                  hint="Capture a photo, speak about it, and let AI build your first listing."
                  action={<Link to="/artisan/products/new" className="k-btn primary">Add your first product</Link>} />
        </KCard>
      )}

      {items && items.map((p) => (
        <KCard key={p.id}>
          <div className="k-row" style={{ alignItems: 'flex-start' }}>
            {p.image_url
              ? <img src={p.image_url} alt={p.title} style={{ width: 86, height: 86, objectFit: 'cover', borderRadius: 12 }} />
              : <div style={{ width: 86, height: 86, borderRadius: 12, background: 'var(--navy-700)' }} />}
            <div style={{ flex: 1, minWidth: 200 }}>
              <div className="k-spread">
                <strong>{p.title}</strong>
                <KBadge tone={LIFECYCLE_TONE[p.lifecycle ?? 'DRAFT']}>{p.lifecycle}</KBadge>
              </div>
              <div className="muted small">{p.short_description}</div>
              <div className="k-row" style={{ marginTop: 8 }}>
                <span className="k-price">{inr(p.price)}</span>
                {p.bulk_price && <span className="muted small">bulk {inr(p.bulk_price)} for {p.bulk_moq}+</span>}
                <span className="muted small">· {p.inventory_mode === 'MADE_TO_ORDER' ? 'Made to order' : `${p.quality_score ?? '–'} · stock`}</span>
              </div>
            </div>
            <div className="k-row">
              {p.lifecycle !== 'PUBLISHED' && <KButton size="sm" onClick={() => void publish(p.id)}>Publish</KButton>}
              {p.lifecycle === 'PUBLISHED' && <KButton size="sm" variant="ghost" onClick={() => void unpause(p.id)}>Pause</KButton>}
            </div>
          </div>
        </KCard>
      ))}
    </div>
  )
}
