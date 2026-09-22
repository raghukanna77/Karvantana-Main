/** KARVANTANA voice intent engine — converts what the artisan said into an app action.
 *
 *  Design: keyword-based intent detection across English + Hindi + major
 *  language keywords. No exact syntax required ("product add karna hai",
 *  "मेरा सामान बेचना है", "add new product" all resolve to ADD_PRODUCT).
 *  The backend AI assistant remains available for open-ended questions; this
 *  layer only handles navigation-grade commands, with a fallback route.
 */

export type Intent =
  | 'ADD_PRODUCT'
  | 'SHOW_ORDERS'
  | 'EARNINGS'
  | 'CUSTOMERS'
  | 'REPEAT_ORDER'
  | 'ASSISTANT'
  | 'PROFILE'
  | 'BULK_OPPORTUNITIES'
  | 'UNKNOWN'

export interface IntentMatch {
  intent: Intent
  /** Where to send the user. */
  route: string
  confidence: number
  /** The matched keyword that decided it (shown as "You said: …" confirmation). */
  matched: string
}

type Rule = { intent: Intent; route: string; keywords: string[] }

const RULES: Rule[] = [
  {
    intent: 'ADD_PRODUCT', route: '/artisan/products/new',
    keywords: [
      'add product', 'new product', 'add item', 'product add', 'naya product', 'नया उत्पाद',
      'उत्पाद जोड़', 'सामान बेचना', 'बेचना है', 'poduct add', 'product sell', 'sell product',
      'பொருள் சேர்', 'புதிய பொருள்', 'కొత్త ఉత్పత్తి', 'ಹೊಸ ಉತ್ಪನ್ನ', 'പുതിയ ഉൽപ്പന്ന', 'নতুন পণ্য',
      'नवीन उत्पादन', 'નવું ઉત્પાદન', 'ਨਵਾਂ ਉਤਪਾਦ',
    ],
  },
  {
    intent: 'SHOW_ORDERS', route: '/artisan/orders',
    keywords: [
      'my order', 'show order', 'orders', 'order list', 'mera order', 'mere order', 'ऑर्डर',
      'आदेश', 'ஆர்டர்', 'ఆర్డర్', 'ಆರ್ಡರ್', 'ഓർഡർ', 'অর্ডার', 'ऑर्डर दिखा', 'today order',
    ],
  },
  {
    intent: 'EARNINGS', route: '/artisan/insights',
    keywords: [
      'earn', 'earning', 'income', 'revenue', 'how much did i', 'kamai', 'kamana', 'कमाई',
      'आय', 'व्यापार', 'வருவாய்', 'ఆదాయం', 'ಆದಾಯ', 'വരുമാനം', 'আয়', 'कमावले', 'business',
    ],
  },
  {
    intent: 'CUSTOMERS', route: '/artisan/customers',
    keywords: [
      'customer', 'my customer', 'buyer list', 'grahak', 'ग्राहक', 'कस्टमर', 'வாடிக்கையாளர்',
      'కస్టమర్', 'ಗ್ರಾಹಕ', 'ഉപഭോക്താവ്', 'ক্রেতা', 'who bought', 'repeat customer',
    ],
  },
  {
    intent: 'REPEAT_ORDER', route: '/artisan/customers',
    keywords: [
      'repeat order', 'reorder', 'dobara order', 'फिर से ऑर्डर', 'दोबारा', 'மீண்டும் ஆர்டர்',
      'मागील ऑर्डर', 'again order',
    ],
  },
  {
    intent: 'BULK_OPPORTUNITIES', route: '/artisan/orders',
    keywords: [
      'bulk', 'wholesale', 'thok', 'थोक', 'मोठा ऑर्डर', 'மொத்தம்', '50 pieces', '100 pieces',
      'many pieces', 'bada order', 'बड़ा ऑर्डर',
    ],
  },
  {
    intent: 'PROFILE', route: '/artisan/profile',
    keywords: [
      'profile', 'my profile', 'account', 'pesha', 'पेशा', 'प्रोफ़ाइल', 'சுயவிவரம்', 'ప్రొఫైల్',
      'प्रोफाइल', 'પ્રોફાઇલ',
    ],
  },
  {
    intent: 'ASSISTANT', route: '/assistant',
    keywords: [
      'help', 'madad', 'मदद', 'सहायता', 'ask', 'question', 'assistant', 'உதவி', 'సహాయం',
      'ماदد', 'मदत', 'how do i', 'kaise',
    ],
  },
]

/** Detect intent from free speech. Longest keyword match wins (more specific first). */
export function detectIntent(text: string): IntentMatch | null {
  const t = ` ${text.toLowerCase().trim()} `
  let best: IntentMatch | null = null
  for (const rule of RULES) {
    for (const kw of rule.keywords) {
      if (t.includes(kw.toLowerCase())) {
        const score = kw.length
        if (!best || score > best.matched.length) {
          best = { intent: rule.intent, route: rule.route, confidence: Math.min(0.6 + score / 60, 0.95), matched: kw }
        }
      }
    }
  }
  return best
}

/** Friendly line confirming what the assistant understood (spoken + shown). */
export function intentConfirmation(match: IntentMatch): string {
  switch (match.intent) {
    case 'ADD_PRODUCT': return 'Opening Add Product — take a photo and tell me about it.'
    case 'SHOW_ORDERS': return 'Opening your orders.'
    case 'EARNINGS': return 'Opening your business numbers.'
    case 'CUSTOMERS': return 'Opening your customers.'
    case 'REPEAT_ORDER': return 'Finding customers who reorder.'
    case 'BULK_OPPORTUNITIES': return 'Opening bulk opportunities.'
    case 'PROFILE': return 'Opening your profile.'
    case 'ASSISTANT': return 'Opening the assistant.'
    default: return ''
  }
}
