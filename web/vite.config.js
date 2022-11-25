import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import preprocess from "svelte-preprocess"

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [svelte({
    preprocess: [
      preprocess({
        postcss: true,
      }),
    ],
  })],
  server: {
    // Make the dev server proxy requests for the backend
    proxy: {
      '^/km/': {
        target: 'http://127.0.0.1:8000',
        headers: {
          'Origin': 'http://127.0.0.1:8000',
        },
      }
    }
  }
})
