import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// KARVANTANA dev server. API target is configurable so this project never
// collides with other services on the machine (default 8014, not 8000).
const API = process.env.KARVANTANA_API_URL ?? 'http://localhost:8014'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    proxy: {
      '/api': API,
      '/media': API,
    },
  },
})
