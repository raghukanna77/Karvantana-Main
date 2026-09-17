/** Shared frontend types mirroring the backend API schemas. */

export type Role = 'ARTISAN' | 'BUYER' | 'B2B_BUYER' | 'CLUSTER_MANAGER' | 'ADMIN'

export interface User {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  role: Role
  preferred_language: string
}

export interface ProductSummary {
  id: string
  title: string
  short_description?: string | null
  price: number
  currency: string
  image_url: string | null
  material?: string | null
  technique?: string | null
  customization_available?: boolean
  bulk_moq?: number | null
  bulk_price?: number | null
  production_days?: number | null
  inventory_mode?: string
  in_stock?: boolean
  artisan_id: string
  lifecycle?: string
  quality_score?: number | null
}

export interface ArtisanInfo {
  id: string
  display_name: string
  craft: string | null
  story: string | null
  location: string
  verification_level: string
  stats: {
    published_products: number
    rating: number | null
    rating_count: number
    verified_orders: number
    repeat_buyers: number
    response_rate: number
    on_time_rate: number
    following?: boolean
  }
  products?: ProductSummary[]
}

export interface ProductDetail extends ProductSummary {
  description?: string | null
  craft_story?: string | null
  origin?: string | null
  dimensions?: string | null
  moq?: number
  attributes?: { key: string; value: string; confidence: number; source: string }[]
  artisan?: ArtisanInfo
  reviews?: { rating: number; text: string | null; verified: boolean; buyer_name: string; created_at: string }[]
  more_from_artisan?: ProductSummary[]
}

export interface OrderItemView {
  id: string
  product_id: string
  title: string
  image_url: string | null
  unit_price: number
  quantity: number
  line_total: number
}

export interface OrderView {
  id: string
  order_number: string
  status: string
  status_label: string
  subtotal: number
  platform_fee: number
  total: number
  currency: string
  is_bulk: boolean
  created_at: string
  items: OrderItemView[]
  history?: { from: string | null; to: string; at: string; note: string | null }[]
}

export interface DashboardTotals {
  revenue: number
  month_revenue: number
  orders: number
  unique_buyers: number
  repeat_buyers: number
  repeat_rate: number
  avg_order_value: number
}

export interface ArtisanDashboard {
  today: { new_orders: number; enquiries: number }
  totals: DashboardTotals
  top_products: { title: string; units: number; revenue: number }[]
  most_viewed: { title: string; views: number; id: string }[]
}

export interface NotificationView {
  id: string
  type: string
  title: string
  body: string | null
  link: string | null
  is_read: boolean
  created_at: string
}

export interface QuoteView {
  id: string
  request_type: 'BULK' | 'CUSTOM'
  request_id: string
  artisan: string
  unit_price: number
  quantity: number
  total: number
  lead_time_days: number
  note: string | null
  status: string
}

export interface BulkRequestView {
  id: string
  title: string
  description: string | null
  quantity: number
  max_unit_price: number | null
  status: string
  parsed?: { quantity?: number; max_unit_price?: number; category?: string; buyer_type?: string; customization?: boolean; confidence?: number } | null
  created_at: string
}

export interface CatalogueOutput {
  title: string
  short_description: string
  description: string
  highlights: string[]
  keywords: string
  confidence: number
  generation_id?: string
  extracted?: Record<string, { value: string; confidence: number; source: string }>
}

export interface PriceRec {
  estimated_cost: number
  market_low: number
  market_high: number
  suggested_price: number
  estimated_margin: number
  margin_pct: number
  demand_signal: string
  explanation: string
  contributions: Record<string, number>
}

export function inr(v: number): string {
  return `₹${v.toLocaleString('en-IN')}`
}
