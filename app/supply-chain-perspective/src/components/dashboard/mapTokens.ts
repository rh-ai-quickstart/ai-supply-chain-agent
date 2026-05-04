/** Resolve PatternFly tokens for Leaflet SVG (canvas/CSS file rules do not apply). */
export function readSemanticToken(name: string, fallback: string): string {
  if (typeof window === 'undefined') {
    return fallback;
  }
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}
