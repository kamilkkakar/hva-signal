import { useState } from "react";
import { truncateToken } from "@/utils/copyableToken";

type CopyableTokenProps = {
  value: string;
  "aria-label"?: string;
  testId?: string;
};

export function CopyableToken({
  value,
  "aria-label": ariaLabel,
  testId,
}: CopyableTokenProps) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <span className="copyable-token" data-testid={testId}>
      <code className="copyable-token-value" title={value} data-full-value={value}>
        {value}
      </code>
      <button
        type="button"
        className="copy-btn"
        aria-label={ariaLabel ?? `Copy ${truncateToken(value)}`}
        data-testid={testId ? `${testId}-copy` : undefined}
        onClick={() => void onCopy()}
      >
        {copied ? "Copied" : "Copy"}
      </button>
    </span>
  );
}
