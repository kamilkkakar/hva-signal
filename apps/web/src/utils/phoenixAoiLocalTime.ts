/** Phoenix v1 historical replay uses 03:00 AOI-local, not browser UTC. */

export const PHOENIX_AOI_LOCAL_HOUR = "03:00";
export const PHOENIX_DEMO_DEFAULT_DATE = "2022-07-01";
export const PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL = `${PHOENIX_DEMO_DEFAULT_DATE}T${PHOENIX_AOI_LOCAL_HOUR}`;

const DATE_PREFIX = /^(\d{4}-\d{2}-\d{2})/;

function phoenixCalendarDate(datetimeLocalValue: string): string {
  const match = DATE_PREFIX.exec(datetimeLocalValue.trim());
  if (!match?.[1]) {
    throw new Error("Analysis time is invalid.");
  }
  return match[1];
}

export function phoenixAoiLocalDatetimeLocalValue(
  datetimeLocalValue: string,
): string {
  return `${phoenixCalendarDate(datetimeLocalValue)}T${PHOENIX_AOI_LOCAL_HOUR}`;
}

export function phoenixAoiLocalAnalysisTime(datetimeLocalValue: string): string {
  return `${phoenixCalendarDate(datetimeLocalValue)}T${PHOENIX_AOI_LOCAL_HOUR}:00`;
}
