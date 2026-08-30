import type { SourceBannerLabel } from "@/utils/sourceBanner";

export type PublicSourceChip =
  | "REPLAY"
  | "CACHED"
  | "LIVE"
  | "PARTIAL"
  | "UNAVAILABLE";

/** Visible source noun. Never a vendor product name. */
export function publicSourceChip(banner: SourceBannerLabel): PublicSourceChip {
  switch (banner) {
    case "FORTYGUARD LIVE":
      return "LIVE";
    case "FORTYGUARD CACHED":
      return "CACHED";
    case "REPLAY":
      return "REPLAY";
    case "PARTIAL":
      return "PARTIAL";
    case "UNAVAILABLE":
      return "UNAVAILABLE";
  }
}

/** First paint is replay. Job banner maps after a result exists. */
export function contextSourceChip(
  banner: SourceBannerLabel,
  hasJob: boolean,
): PublicSourceChip {
  if (!hasJob) {
    return "REPLAY";
  }
  return publicSourceChip(banner);
}
