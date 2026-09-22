/** Field-related background photographs, shown as a soft veil BEHIND the UI.
 *
 *  Sourced from Wikimedia Commons (free licenses, stable URLs, no hotlink
 *  signing). Each entry names the craft context it belongs to so pages can
 *  pick the matching scene: weaving for artisan surfaces, a saree shop for
 *  buying surfaces, block printing for creation/onboarding.
 *
 *  The photos always render behind a warm ivory veil (see .k-pagebg in
 *  theme.css) so text never sits on a busy photo — they stay whisper-quiet,
 *  recognisable, and never overlap or reduce text readability.
 *
 *  Credits (free licenses):
 *  - Silk weaver (Kanchipuram) — McKay Savage, CC BY 2.0
 *  - Maheshwar looms — Yann (Wikimedia), CC BY-SA 3.0
 *  - Saree shop (Ahmedabad) — Wikimedia contributor, CC BY-SA
 *  - Jaipur block printing — Wikimedia contributor, CC BY-SA
 */

export interface BgImage {
  url: string
  /** Short credit shown nowhere by default but kept for attribution. */
  credit: string
  align?: string
}

export const BG: Record<string, BgImage> = {
  /** Weaver at a handloom — artisan workspace pages. */
  weaver: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/a/ae/India_-_Faces_-_silk_weaver_%285208914424%29.jpg',
    credit: 'McKay Savage, CC BY 2.0',
    align: 'center 30%',
  },
  /** Rows of wooden handlooms — dashboard / orders. */
  looms: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/5/51/Looms_at_Rehwa_society%2C_Maheshwari_handloom_sarees_weavers_society%2C_Maheshwar.jpg',
    credit: 'Yann, CC BY-SA 3.0',
    align: 'center 40%',
  },
  /** Colourful saree shop shelves — buying surfaces (explore/product/checkout). */
  sareeShop: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/c/ca/Saree_shop_at_Ratanpol_Ahmedabad.JPG',
    credit: 'Wikimedia contributor, CC BY-SA',
    align: 'center 45%',
  },
  /** Hand block printing — creation / onboarding / assistant. */
  blockPrinting: {
    url: 'https://upload.wikimedia.org/wikipedia/commons/d/d3/Jaipur_03-2016_10_textile_printing.jpg',
    credit: 'Wikimedia contributor, CC BY-SA',
    align: 'center 35%',
  },
}

/** Map each route (prefix match) to the craft scene that fits it. */
export const ROUTE_BG: Array<[prefix: string, key: keyof typeof BG]> = [
  ['/artisan/products/new', 'blockPrinting'],
  ['/artisan/products', 'looms'],
  ['/artisan/orders', 'looms'],
  ['/artisan/customers', 'weaver'],
  ['/artisan/insights', 'looms'],
  ['/artisan', 'weaver'],
  ['/checkout', 'sareeShop'],
  ['/product', 'sareeShop'],
  ['/explore', 'sareeShop'],
  ['/buyer', 'sareeShop'],
  ['/b2b', 'sareeShop'],
  ['/orders', 'sareeShop'],
  ['/assistant', 'blockPrinting'],
  ['/welcome', 'blockPrinting'],
  ['/login', 'weaver'],
]

/** Resolve the background for a pathname. Longest prefix wins. */
export function bgForPath(pathname: string): BgImage | null {
  let best: BgImage | null = null
  let bestLen = -1
  for (const [prefix, key] of ROUTE_BG) {
    if (pathname.startsWith(prefix) && prefix.length > bestLen) {
      best = BG[key] ?? null
      bestLen = prefix.length
    }
  }
  return best
}
