/** State management: auth session + offline mutation queue.
 *  UI → store → api only; no fetches inside components. */

import { create } from 'zustand'
import { api, setToken } from '../core/api'
import type { User } from '../core/types'
import type { Lang } from '../i18n'

// --------------------------------------------------------------- auth store

interface AuthState {
  user: User | null
  hydrated: boolean
  setSession: (user: User, accessToken: string) => void
  clear: () => void
  hydrate: () => void
  refreshUser: () => Promise<void>
}

const SESSION_KEY = 'karvantana.session'

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  hydrated: false,
  setSession: (user, accessToken) => {
    setToken(accessToken)
    localStorage.setItem(SESSION_KEY, JSON.stringify({ user, accessToken }))
    set({ user })
  },
  clear: () => {
    setToken(null)
    localStorage.removeItem(SESSION_KEY)
    set({ user: null })
  },
  hydrate: () => {
    if (get().hydrated) return
    try {
      const raw = localStorage.getItem(SESSION_KEY)
      if (raw) {
        const parsed = JSON.parse(raw) as { user: User; accessToken: string }
        setToken(parsed.accessToken)
        set({ user: parsed.user })
      }
    } catch {
      // corrupted session — start clean
    }
    set({ hydrated: true })
  },
  refreshUser: async () => {
    try {
      const user = await api.get<User>('/auth/me')
      const raw = localStorage.getItem(SESSION_KEY)
      if (raw) {
        const parsed = JSON.parse(raw) as { user: User; accessToken: string }
        localStorage.setItem(SESSION_KEY, JSON.stringify({ ...parsed, user }))
      }
      set({ user })
    } catch {
      /* token expired — session cleared by caller */
    }
  },
}))

// ------------------------------------------------------------- offline queue

export interface QueuedMutation {
  id: string
  kind: 'draft_product' | 'transcript_note' | 'field_edit'
  payload: Record<string, unknown>
  created_at: string
}

interface OfflineState {
  online: boolean
  queue: QueuedMutation[]
  setOnline: (online: boolean) => void
  enqueue: (m: Omit<QueuedMutation, 'id' | 'created_at'>) => void
  dequeue: (id: string) => void
}

const QUEUE_KEY = 'karvantana.offlinequeue'

function loadQueue(): QueuedMutation[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) ?? '[]') as QueuedMutation[]
  } catch {
    return []
  }
}

export const useOffline = create<OfflineState>((set, get) => ({
  online: navigator.onLine,
  queue: loadQueue(),
  setOnline: (online) => set({ online }),
  enqueue: (m) => {
    const item: QueuedMutation = { ...m, id: crypto.randomUUID(), created_at: new Date().toISOString() }
    const queue = [...get().queue, item]
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
    set({ queue })
  },
  dequeue: (id) => {
    const queue = get().queue.filter((q) => q.id !== id)
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
    set({ queue })
  },
}))

// ------------------------------------------------------------ language store

interface UiState {
  lang: Lang
  easyMode: boolean
  voiceGuidance: boolean
  setLang: (l: Lang) => void
  setEasyMode: (on: boolean) => void
  setVoiceGuidance: (on: boolean) => void
}

const LANG_KEY = 'karvantana.lang'
const EASY_KEY = 'karvantana.easyMode'
const VOICE_KEY = 'karvantana.voiceGuidance'

export const useUi = create<UiState>((set) => ({
  lang: (localStorage.getItem(LANG_KEY) as Lang) || 'en',
  easyMode: localStorage.getItem(EASY_KEY) === '1',
  voiceGuidance: localStorage.getItem(VOICE_KEY) !== '0', // default ON — voice-first product
  setLang: (l) => {
    localStorage.setItem(LANG_KEY, l)
    set({ lang: l })
  },
  setEasyMode: (on) => {
    localStorage.setItem(EASY_KEY, on ? '1' : '0')
    set({ easyMode: on })
  },
  setVoiceGuidance: (on) => {
    localStorage.setItem(VOICE_KEY, on ? '1' : '0')
    set({ voiceGuidance: on })
  },
}))
