import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API_PROXY_TARGET || 'http://127.0.0.1:5001',
        changeOrigin: true,
        // Match cluster nginx proxy timeouts for long LLM chat requests.
        timeout: 300_000,
        proxyTimeout: 300_000,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.jsx',
    css: true,
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary'],
    },
  },
})
