import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      // Proxy Flask API during dev so the browser can call relative paths
      '/api/py': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/py/, ''),
      },
      // Use hosted Node API on Vercel so you don't need to run it locally
      '/api/news': {
        target: 'https://news-aggregator-dusky.vercel.app',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/news/, ''),
      },
    },
  },
})
