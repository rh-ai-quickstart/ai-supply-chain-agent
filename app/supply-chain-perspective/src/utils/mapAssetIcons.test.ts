import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAssetDivIcon, PLANE_ICON_PATH } from './mapAssetIcons';

const { divIcon } = vi.hoisted(() => {
  const fn = vi.fn((opts: unknown) => ({ ...(opts as object), _kind: 'divIcon' as const }));
  return { divIcon: fn };
});

vi.mock('leaflet', () => ({
  divIcon,
}));

describe('createAssetDivIcon', () => {
  beforeEach(() => {
    divIcon.mockClear();
  });

  it('uses plane path for air freight', () => {
    createAssetDivIcon('airFreight', { lat: 0, lng: 0 }, { fill: '#fff', stroke: '#000' });
    expect(divIcon.mock.calls[0][0].html as string).toContain(PLANE_ICON_PATH);
  });

  it('uses truck markup for regional non-live assets', () => {
    createAssetDivIcon(
      'regional',
      { lat: 1, lng: 2, is_live: false },
      { fill: '#abc', stroke: '#111' },
    );
    const html = divIcon.mock.calls[0][0].html as string;
    expect(html).toContain('supply-chain-perspective__map-truck-icon');
  });
});
