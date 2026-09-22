/** Artisan product catalogue with lifecycle management. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, serverUrl } from '../../core/api'
import { inr, type ProductSummary } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty } from '../../design'
import { useT } from '../../i18n'

const LIFECYCLE_TONE: Record<string, 'green' | 'blue' | 'gold' | 'red' | undefined> = {
  PUBLISHED: 'green', DRAFT: 'gold', REVIEW_REQUIRED: 'blue', PAUSED: undefined, OUT_OF_STOCK: 'red', ARCHIVED: 'red',
}

export default function ArtisanProducts() {
  const { t } = useT()
  const [items, setItems] = useState<ProductSummary[] | null>(null)

  async function load() {
    const res = await api.get<{ items: ProductSummary[] }>('/products/mine')
    setItems(res.items)
  }
  useEffect(() => { void load() }, [])

  async function publish(id: string) {
    try {
      await api.post(`/products/${id}/publish`)
      void load()
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Could not publish.')
    }
  }
  async function unpause(id: string) {
    try {
      await api.patch(`/products/${id}`, { lifecycle: 'PAUSED' })
      void load()
    } catch (e) {
      window.alert(e instanceof Error ? e.message : 'Could not pause.')
    }
  }

  return (
    <div className="k-stack">
      <div className="k-spread">
        <h2 style={{ fontSize: 22 }}>🧺 {t('nav.products')}</h2>
        <Link to="/artisan/products/new" className="k-btn primary sm">+ {t('home.add_product')}</Link>
      </div>

      {!items && <KCard><div className="k-skeleton" style={{ height: 160 }} /></KCard>}

      {items && items.length === 0 && (
        <KCard>
          <KEmpty icon="📷" title={t('products.none_title')}
                  hint={t('products.none_hint')}
                  action={<Link to="/artisan/products/new" className="k-btn primary">{t('home.add_product')}</Link>} />
        </KCard>
      )}

      {items && items.map((p) => (
        <KCard key={p.id}>
          <div className="k-row" style={{ alignItems: 'flex-start' }}>
            {p.image_url
              ? <img src={serverUrl(p.image_url)} alt={p.title} style={{ width: 86, height: 86, objectFit: 'cover', borderRadius: 12 }} />
              : <div style={{ width: 86, height: 86, borderRadius: 12, background: 'var(--navy-700)' }} />}
            <div style={{ flex: 1, minWidth: 200 }}>
              <div className="k-spread">
                <strong>{p.title}</strong>
                <KBadge tone={LIFECYCLE_TONE[p.lifecycle ?? 'DRAFT']}>{p.lifecycle}</KBadge>
              </div>
              <div className="muted small">{p.short_description}</div>
              <div className="k-row" style={{ marginTop: 8 }}>
                <span className="k-price">{inr(p.price)}</span>
                {p.bulk_price && <span className="muted small">{t('pp.bulk')} {inr(p.bulk_price)} {t('pp.bulk_for')} {p.bulk_moq}+</span>}
                <span className="muted small">· {p.inventory_mode === 'MADE_TO_ORDER' ? t('products.made_to_order') : t('products.in_stock')}</span>
              </div>
            </div>
            <div className="k-row">
              {p.lifecycle !== 'PUBLISHED' && <KButton size="sm" onClick={() => void publish(p.id)}>{t('cta.publish')}</KButton>}
              {p.lifecycle === 'PUBLISHED' && <KButton size="sm" variant="ghost" onClick={() => void unpause(p.id)}>{t('products.pause')}</KButton>}
            </div>
          </div>
        </KCard>
      ))}
    </div>
  )
}
