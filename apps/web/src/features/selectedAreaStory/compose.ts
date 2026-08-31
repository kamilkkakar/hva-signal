import type { AnalysisAreaContextView, ContextFact } from "@/features/areaContext/types";
import { INVENTORY_DISCLAIMER, MAP_MODE_META, Q_DIFFERENT, Q_SUPPORT, Q_THERMAL, Q_VERIFY } from "./copy";
import { directionRules } from "./direction";
import { resolveIdentity } from "./identity";
import { presentThermalA } from "./thermalA";
import { presentThermalB, productThermalStatus } from "./thermalB";
import type {
  ComposeInput,
  PreparednessStatus,
  SelectedAreaDecisionStory,
  StoryFact,
} from "./types";

const FACT_PRIORITY = [
  "canopy_cover_share",
  "median_household_income",
  "share_pre_1980_housing",
  "share_one_person_household",
  "share_age_65_plus",
  "median_year_built",
] as const;

const MAX_FACTS = 6;

function percentValue(value: number, unit: string): string {
  const scaled = unit.toLowerCase().includes("percent") && value <= 1 ? value * 100 : value;
  return `${Math.round(scaled)}`;
}

function quantitySentence(fact: ContextFact): string | null {
  if (fact.value == null || !Number.isFinite(fact.value)) {
    return null;
  }
  switch (fact.kind) {
    case "canopy_cover_share":
      return `Tree canopy covers ${percentValue(fact.value, fact.unit)}% of plantable ground in this analysis area.`;
    case "median_household_income":
      return `Median household income is $${Math.round(fact.value).toLocaleString("en-US")}.`;
    case "share_pre_1980_housing":
      return `${percentValue(fact.value, fact.unit)}% of homes were built before 1980.`;
    case "share_one_person_household":
      return `${percentValue(fact.value, fact.unit)}% of households are one-person households.`;
    case "share_age_65_plus":
      return `${percentValue(fact.value, fact.unit)}% of residents are age 65+.`;
    case "median_year_built":
      return `Median year built of housing stock is ${Math.round(fact.value)}.`;
    default:
      return fact.plain_language_sentence.split(".")[0] + ".";
  }
}

function comparisonClause(fact: ContextFact): string | null {
  if (!fact.comparison_allowed) {
    return null;
  }
  if (fact.comparison === "higher") {
    return "That is above the median of the selected 25-area geography.";
  }
  if (fact.comparison === "lower") {
    return "That is below the median of the selected 25-area geography.";
  }
  if (fact.comparison === "similar") {
    return "That is similar to the median of the selected 25-area geography.";
  }
  return null;
}

function usefulFact(fact: ContextFact): boolean {
  if (fact.quality_status === "MISSING" || fact.quality_status === "SUPPRESSED" || fact.quality_status === "NOT_REQUESTED") {
    return false;
  }
  if (fact.kind === "share_age_65_plus" && fact.quality_status !== "OBSERVED") {
    return false;
  }
  return fact.value != null && Number.isFinite(fact.value);
}

export function selectContextFacts(facts: ContextFact[]): StoryFact[] {
  const byKind = new Map(facts.map((fact) => [fact.kind, fact]));
  const selected: StoryFact[] = [];
  for (const kind of FACT_PRIORITY) {
    if (selected.length >= MAX_FACTS) {
      break;
    }
    const fact = byKind.get(kind);
    if (!fact || !usefulFact(fact)) {
      continue;
    }
    const quantity = quantitySentence(fact);
    if (!quantity) {
      continue;
    }
    const extra = comparisonClause(fact);
    selected.push({
      kind: fact.kind,
      label: fact.label,
      sentence: extra ? `${quantity} ${extra}` : quantity,
      sourceFamily: fact.kind === "canopy_cover_share" ? "canopy" : "acs",
      comparisonAllowed: fact.comparison_allowed,
      qualityStatus: fact.quality_status,
    });
  }
  return selected;
}

function preparednessStatus(
  context: AnalysisAreaContextView | null | undefined,
  coolingStatus: string | null,
): PreparednessStatus {
  const raw = (coolingStatus ?? "").toUpperCase();
  if (raw === "IDENTIFIED") {
    return "IDENTIFIED";
  }
  if (raw === "NOT_IDENTIFIED_IN_DATASET") {
    return "NOT_IDENTIFIED_IN_DATASET";
  }
  const joined = (context?.preparedness ?? []).join(" ").toLowerCase();
  if (joined.includes("identified in the available") && !joined.includes("no site")) {
    return "IDENTIFIED";
  }
  if (joined.includes("no site was identified") || joined.includes("not identified")) {
    return "NOT_IDENTIFIED_IN_DATASET";
  }
  return "UNKNOWN";
}

function sanitizePreparednessLine(line: string): string {
  return line
    .replace(/\s*\([^)]*mag_[^)]*\)/gi, "")
    .replace(/,\s*vintage\s*\d{4}-\d{2}-\d{2}/gi, "")
    .replace(/\binventory row\b/gi, "inventory identification")
    .replace(/\bno row\b/gi, "no site identified")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function preparednessSentences(
  status: PreparednessStatus,
  context: AnalysisAreaContextView | null | undefined,
): string[] {
  const incoming = (context?.preparedness ?? [])
    .filter((line) => !/no cooling site/i.test(line))
    .map(sanitizePreparednessLine)
    .filter((line) => line.length > 0);
  if (incoming.length) {
    return incoming;
  }
  if (status === "IDENTIFIED") {
    return [
      "Heat-relief site(s) are identified in the available regional inventory. Identification is not proof that cooling is available.",
    ];
  }
  if (status === "NOT_IDENTIFIED_IN_DATASET") {
    return [
      "No Heat Relief Network site was identified in the available dataset for this analysis area. This does not establish that no cooling resource exists.",
    ];
  }
  return ["Cooling inventory status is unknown for this analysis area."];
}

function coolingStatusFrom(input: ComposeInput): string | null {
  const geoid = input.selectedGeoid ?? input.context?.census_tract_geoid ?? null;
  const zone = input.document?.zones.find(
    (row) => row.census_tract_geoid === geoid || row.zone_id === geoid,
  );
  return zone?.cooling_site_status ?? null;
}

/** Compose product story on the client. Do not send thermal_sentence to GET /context. */
export function composeSelectedAreaStory(input: ComposeInput = {}): SelectedAreaDecisionStory {
  const geoid = input.selectedGeoid ?? input.context?.census_tract_geoid ?? null;
  const identity = resolveIdentity(geoid);
  const a = presentThermalA(input.result ?? null, identity.inCatalog ? geoid : null);
  const b = presentThermalB(identity.inCatalog ? geoid : null);
  const status = productThermalStatus({
    aHasRealPane: a.hasRealPane,
    bTemperatureC: b.temperatureC,
  });
  const facts = selectContextFacts(input.context?.context_facts ?? []);
  const preparedness = preparednessStatus(input.context, coolingStatusFrom(input));
  const rules = directionRules({
    inCatalog: identity.inCatalog,
    a,
    b,
    hasContextFacts: facts.length > 0,
    preparedness,
  });

  return {
    identity,
    questions: {
      thermal: {
        label: Q_THERMAL,
        status,
        a,
        b,
      },
      different: {
        label: Q_DIFFERENT,
        facts,
      },
      support: {
        label: Q_SUPPORT,
        status: preparedness,
        sentences: preparednessSentences(preparedness, input.context),
        disclaimer: INVENTORY_DISCLAIMER,
      },
      verify: {
        label: Q_VERIFY,
        rules,
      },
    },
    sources: {
      fortyguard: [
        a.hasRealPane ? "FortyGuard replay — Signal A historical order" : "FortyGuard replay — no A pane",
        b.kind === "cached"
          ? "FortyGuard cached — 2025-07-15 03:00 America/Phoenix"
          : "FortyGuard cached — no selected-zone °C",
      ],
      acs: facts.filter((fact) => fact.sourceFamily === "acs").map((fact) => fact.label),
      canopy: facts.filter((fact) => fact.sourceFamily === "canopy").map((fact) => fact.label),
      mag: ["MAG heat-relief network — partial regional inventory"],
    },
    mapModes: [...MAP_MODE_META],
    combined_score_authorized: false,
    vulnerability_score_authorized: false,
  };
}

export function storyPublicBlob(story: SelectedAreaDecisionStory): string {
  return [
    story.identity.label ?? "",
    story.questions.thermal.label,
    story.questions.thermal.status,
    story.questions.thermal.a.kind,
    story.questions.thermal.a.q_A == null ? "" : String(story.questions.thermal.a.q_A),
    story.questions.thermal.b.wording,
    story.questions.thermal.b.temperatureC == null
      ? ""
      : `${story.questions.thermal.b.temperatureC.toFixed(1)} °C`,
    ...story.questions.different.facts.map((fact) => fact.sentence),
    ...story.questions.support.sentences,
    story.questions.support.disclaimer,
    ...story.questions.verify.rules.map((rule) => rule.text),
  ]
    .join("\n")
    .toLowerCase();
}
