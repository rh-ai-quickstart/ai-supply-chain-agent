import { defineConfig } from 'vitest/config';

export default defineConfig({
  define: {
    __SUPPLY_CHAIN_PLUGIN_HTTP_BASE__: JSON.stringify('/api/plugins/supply-chain-perspective/'),
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
