/** Delivery address form — captured before the order is created so the
 *  checkout page always receives a complete order. Saved for reuse. */
import { useState } from 'react'
import { KButton, KInput, KLabel } from '../../design'
import { useT } from '../../i18n'

export interface Address { line1: string; city: string; pincode: string }

export default function AddressForm({ onSaved, onCancel }: {
  onSaved: (a: Address) => void
  onCancel?: () => void
}) {
  const { t } = useT()
  const [a, setA] = useState<Address>(() => {
    try { return JSON.parse(localStorage.getItem('karvantana.address') ?? '{}') as Address }
    catch { return { line1: '', city: '', pincode: '' } }
  })
  const valid = a.line1.trim().length > 0 && a.pincode.trim().length >= 5

  return (
    <div className="k-stack">
      <h3>{t('addr.title')}</h3>
      <KLabel>{t('addr.line1')}</KLabel>
      <KInput value={a.line1} onChange={(e) => setA({ ...a, line1: e.target.value })} placeholder={t('addr.line1_ph')} />
      <div className="k-row">
        <div style={{ flex: 1 }}>
          <KLabel>{t('addr.city')}</KLabel>
          <KInput value={a.city} onChange={(e) => setA({ ...a, city: e.target.value })} />
        </div>
        <div style={{ flex: 1 }}>
          <KLabel>{t('addr.pincode')}</KLabel>
          <KInput value={a.pincode} onChange={(e) => setA({ ...a, pincode: e.target.value })} inputMode="numeric" />
        </div>
      </div>
      <div className="k-row" style={{ marginTop: 10 }}>
        <KButton onClick={() => onSaved(a)} disabled={!valid}>{t('addr.continue')}</KButton>
        {onCancel && <KButton variant="ghost" onClick={onCancel}>{t('cta.cancel')}</KButton>}
      </div>
    </div>
  )
}
