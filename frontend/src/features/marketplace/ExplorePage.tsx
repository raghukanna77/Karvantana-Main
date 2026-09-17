/** Buyer marketplace: natural-language search with visible interpretation. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type ProductSummary } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KInput } from '../../design'

interface Feed {
  items: ProductSummary[]
  total: number
  interpreted: Record<string, unknown> | null
}

export default function ExplorePage() {
  const [q, setQ] = useState('')
  const [feed, setFeed] = useState<Feed | null>(null)
  const [loading, setLoading] = useState(true)

  async function search(query = q) {
    setLoading(true)
    try {
      setFeed(await api.get<Feed>(`/products?q=${encodeURIComponent(query)}`))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void search('') /* eslint-disable-line react-hooks/exhaustive-deps */ }, [])

  return (
    <div className="k-stack" style={{ paddingBottom: 40 }}>
      <div>
        <h1 style={{ fontSize: 24 }}>Explore handmade</h1>
        <div className="muted small">Every product belongs to a real artisan — tap through to meet them.</div>
      </div>

      <div className="k-row">
        <KInput style={{ flex: 1 }}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void search() }}
                placeholder='Try: "handwoven saree under 1500" or "100 bamboo baskets for a corporate event"' />
        <KButton onClick={() => void search()}>Search</KButton>
      </div>

      {feed?.interpreted && (
        <div className="k-row">
          <span className="muted small">Understood as:</span>
          {Object.entries(feed.interpreted).map(([k, v]) => (
            <KBadge key={k} tone="blue">{k.replace('_', ' ')}: {String(v)}</KBadge>
          ))}
        </div>
      )}

      {loading && <div className="k-grid">{[1, 2, 3, 4].map((i) => <KCard key={i}><div className="k-skeleton" style={{ height: 220 }} /></KCard>)}</div>}

      {feed && feed.items.length === 0 && !loading && (
        <KCard><KEmpty icon="🔍" title="Nothing matched that search"
                       hint="Try a material (bamboo, cotton), a craft (handloom), or a state." /></KCard>
      )}

      {feed && feed.items.length > 0 && (
        <div className="k-grid">
          {feed.items.map((p) => (
            <Link key={p.id} to={`/product/${p.id}`}>
              <KCard className="k-product-card">
                {p.image_url ? <img className="ph" src={p.image_url} alt={p.title} loading="lazy" /> : <div className="ph" />}
                <div className="body">
                  <strong style={{ fontSize: 14.5 }}>{p.title}</strong>
                  <span className="muted small">{p.material}{p.technique ? ` · ${p.technique}` : ''}</span>
                  <div className="k-spread" style={{ marginTop: 'auto' }}>
                    <span className="k-price">{inr(p.price)}</span>
                    <span className="k-row" style={{ gap: 4 }}>
                      {p.customization_available && <KBadge tone="violet">custom</KBadge>}
                      {p.bulk_moq && <KBadge tone="gold">bulk</KBadge>}
                    </span>
                  </div>
                </div>
              </KCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
