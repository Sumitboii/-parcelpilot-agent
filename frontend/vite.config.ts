import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command }) => ({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    proxy: command === 'serve' ? {
      '/chat': 'http://localhost:8000',
      '/confirm': 'http://localhost:8000',
      '/proactive': 'http://localhost:8000',
    } : undefined,
  },
}))
