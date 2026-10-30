import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const localExecution = env.VITE_LOCAL_EXECUTION === 'true';
  return {
    base: env.VITE_BASE_PATH || '/',
    plugins: [svelte()],
    optimizeDeps: { exclude: ['@sqlite.org/sqlite-wasm'] },
    server: { proxy: localExecution ? undefined : { '/api': 'http://127.0.0.1:8000' } },
  };
});
