/** Judge Hybrid IA shell. Default ON on feat/i-ux-shell only. */

export const JUDGE_SHELL_FLAG = "VITE_HVA_JUDGE_SHELL";

function envValue(name: string): string | boolean | undefined {
  const env = import.meta.env as Record<string, string | boolean | undefined>;
  return env[name];
}

/** Off only when explicitly `0` / `false`. Unset means ON. */
export function isJudgeShellEnabled(): boolean {
  const value = envValue(JUDGE_SHELL_FLAG);
  return value !== false && value !== "0" && value !== "false";
}
