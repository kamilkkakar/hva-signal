import { SignalBSection } from "@/features/signals/SignalBSection";
import "@/features/signals/signals.css";
import { GATE1_TCM_JOINS } from "./publicBGate";
import "./signalB.css";
import { phoenixDemoUnavailableSelectedTimeView } from "./unavailable";

/**
 * Public Signal B stays disabled. This is the honest unavailable contract,
 * not a temperature product. GATE 1 stands (TCM 0/25).
 */
export function SignalBUnavailableDisclosure() {
  const view = phoenixDemoUnavailableSelectedTimeView();
  return (
    <div
      className="signal-b-unavailable-disclosure"
      data-testid="signal-b-unavailable-disclosure"
      data-public-signal-b="disabled"
      data-gate1="stands"
      data-tcm-joins={GATE1_TCM_JOINS}
      data-capability="integration-testing"
    >
      <SignalBSection view={view} />
    </div>
  );
}
