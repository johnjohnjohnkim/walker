/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    // MapLibre loads its web worker from a file next to its main module.
    // Pre-bundling moves the main module and breaks that relative URL.
    optimizeDeps: {
      exclude: ['maplibre-gl'],
    },
    server: {
      // In development the browser talks only to Vite, which forwards /api to
      // Django. That keeps everything same-origin, so no CORS setup is needed.
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          // Send the backend's own host name, so Django's ALLOWED_HOSTS check
          // passes even when the app is opened from another device.
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
    },
  }
})
