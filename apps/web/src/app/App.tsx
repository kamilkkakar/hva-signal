import { CommandCenterShell } from "../features/command-center/CommandCenterShell";
import { JudgeShell } from "../features/judgeShell";
export function App() {
  return import.meta.env.VITE_HVA_JUDGE_SHELL === "0" ? <CommandCenterShell /> : <JudgeShell />;
}
