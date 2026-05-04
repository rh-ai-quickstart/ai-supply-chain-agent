/**
 * Returns the landing page URL for the Supply Chain perspective.
 * The console calls this when the perspective is selected.
 */
export const getPerspectiveLandingPageURL = (
  flags: Record<string, boolean>,
  isFirstVisit: boolean,
): string => {
  return '/supply-chain/dashboard';
};
/**
 * Returns the relative redirect URL for the import flow into this perspective.
 */
export const getImportRedirectURL = (namespace: string): string => {
  return '/supply-chain/dashboard';
};