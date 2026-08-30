/** Client pair for HVA_PUBLIC_CONTEXT. RC-v2 default ON. Set 0 to disable. */

export const HVA_PUBLIC_CONTEXT_FLAG = "HVA_PUBLIC_CONTEXT";
export const VITE_HVA_PUBLIC_CONTEXT_FLAG = "VITE_HVA_PUBLIC_CONTEXT";

function rawFlag(): string {
  const env = import.meta.env as Record<string, string | boolean | undefined>;
  const vite = env[VITE_HVA_PUBLIC_CONTEXT_FLAG];
  if (vite !== undefined && vite !== "") {
    return String(vite);
  }
  return "1";
}

export function isPublicContextEnabled(raw: string = rawFlag()): boolean {
  const value = raw.trim().toLowerCase();
  return value === "1" || value === "true" || value === "yes" || value === "on";
}
