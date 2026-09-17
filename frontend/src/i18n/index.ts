/** Frontend i18n: translation keys with 10-language architecture.
 *  English is the fallback catalog; regional catalogs are seeded for key
 *  strings and gracefully fall back (t() never crashes on a missing key). */

export type Lang = 'en' | 'ta' | 'hi' | 'te' | 'kn' | 'ml' | 'bn' | 'mr' | 'gu' | 'pa'

export const LANGUAGES: { code: Lang; name: string }[] = [
  { code: 'en', name: 'English' },
  { code: 'ta', name: 'தமிழ் (Tamil)' },
  { code: 'hi', name: 'हिन्दी (Hindi)' },
  { code: 'te', name: 'తెలుగు (Telugu)' },
  { code: 'kn', name: 'ಕನ್ನಡ (Kannada)' },
  { code: 'ml', name: 'മലയാളം (Malayalam)' },
  { code: 'bn', name: 'বাংলা (Bengali)' },
  { code: 'mr', name: 'मराठी (Marathi)' },
  { code: 'gu', name: 'ગુજરાતી (Gujarati)' },
  { code: 'pa', name: 'ਪੰਜਾਬੀ (Punjabi)' },
]

type Dict = Record<string, string>

const en: Dict = {
  'app.name': 'KARVANTANA',
  'app.tagline': 'From Craft to Commerce',
  'nav.home': 'Home',
  'nav.products': 'Products',
  'nav.orders': 'Orders',
  'nav.insights': 'Insights',
  'nav.profile': 'Profile',
  'nav.explore': 'Explore',
  'nav.saved': 'Saved',
  'nav.add_product': 'Add Product',
  'nav.speak': 'Speak',
  'cta.start_selling': 'Start Selling',
  'cta.explore_products': 'Explore Products',
  'cta.buy_from_artisan': 'Buy from Artisan',
  'cta.request_custom': 'Request Custom',
  'cta.request_bulk': 'Request Bulk Quote',
  'cta.follow': 'Follow Artisan',
  'cta.save': 'Save Artisan',
  'cta.buy_again': 'Buy Again From This Artisan',
  'cta.approve': 'Approve',
  'cta.edit': 'Edit',
  'cta.regenerate': 'Regenerate',
  'cta.accept': 'Accept',
  'cta.skip': 'Skip',
  'cta.publish': 'Publish',
  'auth.sign_in': 'Sign in',
  'auth.create_account': 'Create account',
  'auth.email': 'Email',
  'auth.password': 'Password',
  'auth.phone': 'Mobile number',
  'auth.full_name': 'Your name',
  'auth.send_code': 'Send code',
  'auth.otp_code': '6-digit code',
  'product.title': 'Product title',
  'product.price': 'Price',
  'product.material': 'Material',
  'product.technique': 'Technique',
  'order.awaiting_payment': 'Awaiting payment',
  'order.confirmed': 'Confirmed',
  'order.completed': 'Completed',
  'ai.creating_catalogue': 'Creating catalogue…',
  'ai.review_and_approve': 'Check the details, then approve.',
  'ai.needs_confirmation': 'AI is not certain about this detail. Please confirm.',
  'offline.banner': 'Offline Mode',
  'offline.pending': '{n} change(s) waiting to sync',
}

const ta: Dict = {
  'app.tagline': 'கைவினையிலிருந்து வணிகம் வரை',
  'nav.home': 'முகப்பு',
  'nav.products': 'பொருட்கள்',
  'nav.orders': 'ஆர்டர்கள்',
  'nav.insights': 'நுண்ணறிவு',
  'nav.profile': 'சுயவிவரம்',
  'nav.explore': 'உலாவு',
  'nav.add_product': 'பொருள் சேர்',
  'cta.start_selling': 'விற்கத் தொடங்குங்கள்',
  'cta.explore_products': 'பொருட்களைப் பாருங்கள்',
  'ai.creating_catalogue': 'விளக்கப்பட்டியல் உருவாக்கப்படுகிறது…',
  'order.awaiting_payment': 'பணம் செலுத்த எதிர்பார்க்கிறது',
  'order.confirmed': 'உறுதிப்படுத்தப்பட்டது',
  'order.completed': 'முடிந்தது',
}

const hi: Dict = {
  'app.tagline': 'शिल्प से वाणिज्य तक',
  'nav.home': 'होम',
  'nav.products': 'उत्पाद',
  'nav.orders': 'ऑर्डर',
  'nav.insights': 'अंतर्दृष्टि',
  'nav.profile': 'प्रोफ़ाइल',
  'nav.explore': 'खोजें',
  'nav.add_product': 'उत्पाद जोड़ें',
  'cta.start_selling': 'बेचना शुरू करें',
  'cta.explore_products': 'उत्पाद देखें',
  'ai.creating_catalogue': 'कैटलॉग बनाया जा रहा है…',
  'order.awaiting_payment': 'भुगतान प्रतीक्षित',
  'order.confirmed': 'पुष्ट हो गया',
  'order.completed': 'पूर्ण',
}

const catalogs: Partial<Record<Lang, Dict>> = { en, ta, hi }
const regionalNotes: Partial<Record<Lang, string>> = {
  te: 'Telugu catalog pending community review — falling back to English.',
  kn: 'Kannada catalog pending community review — falling back to English.',
  ml: 'Malayalam catalog pending community review — falling back to English.',
  bn: 'Bengali catalog pending community review — falling back to English.',
  mr: 'Marathi catalog pending community review — falling back to English.',
  gu: 'Gujarati catalog pending community review — falling back to English.',
  pa: 'Punjabi catalog pending community review — falling back to English.',
}

export function translate(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  const dict = catalogs[lang] ?? en
  let text = dict[key] ?? en[key] ?? key
  if (vars) {
    for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, String(v))
  }
  return text
}

export function catalogNote(lang: Lang): string | undefined {
  return regionalNotes[lang]
}
