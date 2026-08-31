import type { StoryFact } from "@/features/selectedAreaStory/types";
import { interpretContextFact } from "./narrative/pattern";
import type { ContextComparison } from "./narrative/types";

function valueDisplayFromSentence(fact: StoryFact): string {
  if (fact.kind === "median_household_income") {
    const match = fact.sentence.match(/\$[\d,]+/);
    if (match) {
      const dollars = Number(match[0].replace(/[$,]/g, ""));
      if (Number.isFinite(dollars)) {
        return `$${(dollars / 1000).toFixed(dollars % 1000 === 0 ? 0 : 1)}k`;
      }
      return match[0];
    }
  }
  if (fact.kind === "median_year_built") {
    const match = fact.sentence.match(/\b(19|20)\d{2}\b/);
    return match?.[0] ?? "—";
  }
  const pct = fact.sentence.match(/(\d+(?:\.\d+)?)%/);
  if (pct) {
    return `${pct[1]}%`;
  }
  return fact.label;
}

function comparisonFromSentence(
  fact: StoryFact,
): "higher" | "lower" | "similar" | null {
  if (!fact.comparisonAllowed) {
    return null;
  }
  if (/above the median/i.test(fact.sentence)) {
    return "higher";
  }
  if (/below the median/i.test(fact.sentence)) {
    return "lower";
  }
  if (/similar to the median/i.test(fact.sentence)) {
    return "similar";
  }
  return null;
}

export function contextComparisonsFromFacts(facts: StoryFact[]): ContextComparison[] {
  return facts.map((fact) => {
    const comparison = comparisonFromSentence(fact);
    const interpreted = interpretContextFact({
      kind: fact.kind,
      comparison,
      comparisonAllowed: fact.comparisonAllowed,
    });
    return {
      kind: fact.kind,
      label: fact.label,
      valueDisplay: valueDisplayFromSentence(fact),
      comparison,
      comparisonAllowed: fact.comparisonAllowed,
      tone: interpreted.tone,
      interpretation: interpreted.interpretation,
    };
  });
}
