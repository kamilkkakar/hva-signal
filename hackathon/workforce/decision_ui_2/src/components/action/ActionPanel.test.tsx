import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ActionPanel } from "./ActionPanel";

describe("ActionPanel", () => {
  it("uses evidence sections and no traffic-light language", () => {
    render(<ActionPanel questionId="evidence-next" />);
    const text = screen.getByTestId("action-panel").textContent ?? "";
    expect(text).toContain("What the evidence shows");
    expect(text).toContain("Why it matters");
    expect(text).toContain("Direction");
    expect(text).toContain("What to verify next");
    expect(text).toContain("What this does not establish");
    expect(text.toLowerCase()).not.toContain("low risk");
    expect(text.toLowerCase()).not.toContain("high risk");
  });
});
