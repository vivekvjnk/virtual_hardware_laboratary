import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    watch: {
      ignored: ['**/node_modules/**', '**/dist/**'],
    },
  },
  // This completely mutes the source map warnings from flooding the terminal
  logLevel: 'info',
})