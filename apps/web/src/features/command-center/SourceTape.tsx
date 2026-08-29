import type { SourceBannerLabel } from "@/utils/sourceBanner";
import { SOURCE_TAPE_SEGMENTS } from "@/utils/sourceBanner";

type SourceTapeProps = {
  active: SourceBannerLabel;
};

export function SourceTape({ active }: SourceTapeProps) {
  return (
    <div className="source-cluster">
      <p className="source-banner" data-testid="source-banner">
        Thermal source: <strong>{active}</strong>
      </p>
      <ol className="source-tape" aria-label="FortyGuard provenance tape">
        {SOURCE_TAPE_SEGMENTS.map((segment) => {
          const isActive = segment.banner === active;
          return (
            <li
              key={segment.id}
              className="source-tape-cell"
              data-active={isActive ? "true" : "false"}
              data-segment={segment.id}
            >
              <span className="source-tape-tick" aria-hidden="true" />
              {segment.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
