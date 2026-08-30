/** Optional absolute API origin for isolated preview/e2e. Empty keeps same-origin proxy. */
export function apiUrl(path: string): string {
  const base = String(import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  return `${base}${path}`;
}
