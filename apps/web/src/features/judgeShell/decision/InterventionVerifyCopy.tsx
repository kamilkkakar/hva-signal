import {
  COOL_CORRIDORS_LINE,
  COOLSEAL_LINE,
  VERIFY_MATURITY,
  VERIFY_NOT_EFFECT,
  VERIFY_TITLE,
} from "./copy";
import { StoryCard } from "./StoryCard";

export function InterventionVerifyCopy() {
  return (
    <StoryCard title={VERIFY_TITLE} status="AVAILABLE" testId="verify-before-action">
      <p className="decision-status-line">{VERIFY_MATURITY}</p>
      <p>{COOLSEAL_LINE}</p>
      <p>{COOL_CORRIDORS_LINE}</p>
      <p className="decision-disclosure">{VERIFY_NOT_EFFECT}</p>
    </StoryCard>
  );
}
