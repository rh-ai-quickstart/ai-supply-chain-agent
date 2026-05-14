import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

const sdkMocks = vi.hoisted(() => {
  const consoleFetchJSON = vi.fn();
  const consoleFetchJSONPost = vi.fn();
  Object.assign(consoleFetchJSON, { post: consoleFetchJSONPost });
  const consoleFetch = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({}),
    text: async () => '',
  }));
  return { consoleFetchJSON, consoleFetchJSONPost, consoleFetch };
});

vi.mock('@openshift-console/dynamic-plugin-sdk', () => ({
  consoleFetchJSON: sdkMocks.consoleFetchJSON,
  consoleFetch: sdkMocks.consoleFetch,
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
