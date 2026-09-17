/** Public landing page — From Craft to Commerce. */

import { Link } from 'react-router-dom'
import { KButton, KCard } from '../../design'

const STEPS = [
  ['📷', 'Capture', 'Snap a photo and speak about your craft in your own language.'],
  ['✨', 'AI builds your catalogue', 'Voice becomes a professional, multilingual product listing — you approve every word.'],
  ['💰', 'Price with confidence', 'See your costs, the market range and a suggested price you can accept, edit or skip.'],
  ['🌐', 'Meet the right buyers', 'Consumers, boutiques, hotels and institutions find you — including bulk orders.'],
  ['🔁', 'Sell again & again', 'Buyers follow you, reorder directly, and your reputation grows with every order.'],
] as const

export default function LandingPage() {
  return (
    <div>
      <section className="container k-weave" style={{ padding: '72px 20px 56px', textAlign: 'center' }}>
        <div className="k-badge violet" style={{ marginBottom: 18 }}>AI-Powered Digital Business Manager for Artisans</div>
        <h1 className="hero-title">From <span className="grad">Craft</span><br />to <span className="grad">Commerce</span></h1>
        <p className="muted" style={{ maxWidth: 640, margin: '18px auto 28px', fontSize: 17 }}>
          Give KARVANTANA a photo and describe your product in your own language. Our AI helps turn it into a
          professional digital business — catalogue, pricing, buyers and repeat orders.
        </p>
        <div className="k-row" style={{ justifyContent: 'center' }}>
          <Link to="/login"><KButton size="lg">Start Your Digital Business</KButton></Link>
          <Link to="/explore"><KButton size="lg" variant="ghost">Explore Artisan Products</KButton></Link>
        </div>
      </section>

      <section className="container" style={{ padding: '30px 20px' }}>
        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
          <KCard>
            <div style={{ fontSize: 30 }}>🧵</div>
            <h3 style={{ margin: '8px 0 6px' }}>The problem</h3>
            <p className="muted small">Artisans already make extraordinary products. What's missing is the digital machinery: catalogues, pricing, buyers, trust, repeat customers.</p>
          </KCard>
          <KCard>
            <div style={{ fontSize: 30 }}>🤝</div>
            <h3 style={{ margin: '8px 0 6px' }}>Not another marketplace</h3>
            <p className="muted small">Marketplaces connect buyers to products. KARVANTANA connects buyers back to the artisan — and makes artisans digitally commerce-ready.</p>
          </KCard>
          <KCard>
            <div style={{ fontSize: 30 }}>📈</div>
            <h3 style={{ margin: '8px 0 6px' }}>A business, not a listing</h3>
            <p className="muted small">Smart pricing, demand insights, B2B bulk requests, reputation and direct reorders — the full loop from craft to sustainable income.</p>
          </KCard>
        </div>
      </section>

      <section className="container" style={{ padding: '40px 20px' }}>
        <h2 className="section-title">How it works</h2>
        <div className="k-stack">
          {STEPS.map(([icon, title, body], i) => (
            <div key={title} className="k-row" style={{ alignItems: 'flex-start' }}>
              <span className="step-num">{i + 1}</span>
              <div>
                <div style={{ fontWeight: 700 }}>{icon} {title}</div>
                <div className="muted small">{body}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="container" style={{ padding: '20px 20px 40px' }}>
        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          <KCard className="pad-lg">
            <div className="k-badge blue">For Artisans & SHGs</div>
            <h3 style={{ margin: '12px 0 8px' }}>Your craft deserves more than a one-day fair.</h3>
            <ul className="muted small" style={{ lineHeight: 2, paddingLeft: 18 }}>
              <li>🎙️ Speak your product — AI writes the listing</li>
              <li>💰 Smart pricing with "Why this price?"</li>
              <li>📦 Bulk & custom requests from verified buyers</li>
              <li>📊 Real insights from your real orders</li>
            </ul>
            <Link to="/login"><KButton block style={{ marginTop: 14 }}>Start Selling</KButton></Link>
          </KCard>
          <KCard className="pad-lg">
            <div className="k-badge gold">For Buyers, B2B & Institutions</div>
            <h3 style={{ margin: '12px 0 8px' }}>Source handmade directly from the makers.</h3>
            <ul className="muted small" style={{ lineHeight: 2, paddingLeft: 18 }}>
              <li>🔎 Describe what you need in plain language</li>
              <li>🧑‍🏭 Know the artisan behind every product</li>
              <li>🧾 Quotes, purchase orders, repeat procurement</li>
              <li>✅ Verified-purchase reviews only</li>
            </ul>
            <Link to="/explore"><KButton block variant="gold" style={{ marginTop: 14 }}>Explore Products</KButton></Link>
          </KCard>
        </div>
      </section>

      <footer className="container" style={{ padding: '30px 20px 60px', textAlign: 'center' }}>
        <hr className="k-divider" />
        <p className="muted small">
          KARVANTANA — From Craft to Commerce. AI and integrations run in clearly-labeled demo mode until real
          credentials are configured. No metric on this platform is invented.
        </p>
      </footer>
    </div>
  )
}
