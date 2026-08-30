import {
  MISSING_DISPLAY,
  POSITION_MEANING,
  RELATIVE_ORDER_LABEL,
  formatQuantile4,
  formatRelativeOrder,
  storySourceLabel,
} from "./policy";
import type { InteractionZone, ProductSourceLabel, ZoneDetail } from "./types";

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

/** Calendar date from an AOI-local stamp. Does not shift across timezones. */
export function formatObservationLabel(stamp: string | null | undefined): string {
  if (!stamp) {
    return MISSING_DISPLAY;
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(stamp);
  if (!match) {
    return stamp;
  }
  const year = match[1];
  const month = Number(match[2]);
  const day = Number(match[3]);
  const monthName = MONTHS[month - 1];
  if (!monthName || !Number.isFinite(day) || day < 1) {
    return stamp;
  }
  return `${day} ${monthName} ${year} · 03:00 local`;
}

export function emptyStoryFields(input: {
  observation_label: string;
  source_label: ProductSourceLabel;
}): Pick<
  InteractionZone,
  | "q_A_display"
  | "q_A_value"
  | "relative_order"
  | "relative_order_of"
  | "observation_label"
  | "source_story"
  | "position_shown"
> {
  return {
    q_A_display: null,
    q_A_value: null,
    relative_order: null,
    relative_order_of: null,
    observation_label: input.observation_label,
    source_story: storySourceLabel(input.source_label),
    position_shown: false,
  };
}

export function authorizedStoryFields(input: {
  q_A: number | null;
  order: number | null;
  of: number;
  observation_label: string;
  source_label: ProductSourceLabel;
}): ReturnType<typeof emptyStoryFields> {
  const qOk = input.q_A != null && Number.isFinite(input.q_A);
  const orderOk = input.order != null && Number.isFinite(input.order) && input.of >= 1;
  return {
    q_A_display: qOk ? formatQuantile4(input.q_A) : null,
    q_A_value: qOk ? input.q_A : null,
    relative_order: orderOk ? input.order : null,
    relative_order_of: orderOk ? input.of : null,
    observation_label: input.observation_label,
    source_story: storySourceLabel(input.source_label),
    position_shown: qOk,
  };
}

export function relativeOrderLine(zone: InteractionZone): string | null {
  if (zone.relative_order == null || zone.relative_order_of == null) {
    return null;
  }
  const line = formatRelativeOrder(zone.relative_order, zone.relative_order_of);
  return line === MISSING_DISPLAY ? null : `${RELATIVE_ORDER_LABEL} — ${zone.relative_order} of ${zone.relative_order_of}`;
}

export function positionPct(value: number | null | undefined): number | null {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  const clamped = Math.min(1, Math.max(0, value));
  return Math.round(clamped * 1000) / 10;
}

export function storyFromZone(zone: InteractionZone): Pick<
  ZoneDetail,
  | "observation_label"
  | "source_story"
  | "position_meaning"
  | "position_shown"
  | "position_pct"
  | "relative_order_line"
  | "q_A_display"
> {
  return {
    observation_label: zone.observation_label,
    source_story: zone.source_story,
    position_meaning: POSITION_MEANING,
    position_shown: zone.position_shown,
    position_pct: zone.position_shown ? positionPct(zone.q_A_value) : null,
    relative_order_line: zone.position_shown ? relativeOrderLine(zone) : null,
    q_A_display: zone.position_shown ? zone.q_A_display : null,
  };
}
