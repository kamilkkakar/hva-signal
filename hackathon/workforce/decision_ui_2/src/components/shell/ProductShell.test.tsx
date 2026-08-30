import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { QUESTIONS } from "@/ia/questions";
import { resetDecisionStore } from "@/state/store";
import { App } from "@/App";
import { assertNoForbidden } from "@/test/forbidden";

afterEach(() => {
  cleanup();
  resetDecisionStore();
});

describe("Decision UI 2.0 public shell", () => {
  it("renders question-first navigation without technical IDs", () => {
    render(<App />);
    const nav = screen.getByTestId("question-nav");
    for (const question of QUESTIONS) {
      expect(within(nav).getByRole("button", { name: new RegExp(question.prompt, "i") })).toBeTruthy();
    }
    const text = document.body.textContent ?? "";
    expect(() => assertNoForbidden(text)).not.toThrow();
    expect(text).not.toMatch(/Analysis area 1[\s\S]{0,40}GEOID/);
    expect(screen.getByTestId("evidence-ledger")).toBeTruthy();
    expect(screen.getByTestId("action-panel")).toBeTruthy();
  });

  it("keeps temporal story values unpublished", () => {
    render(<App />);
    expect(screen.getByTestId("story-card-selected_window_state")).toHaveAttribute(
      "data-pending",
      "true",
    );
    expect(screen.queryByText("+0.8")).toBeNull();
    expect(screen.queryByText("91 / 92 nights")).toBeNull();
    expect(screen.getAllByText("Not published").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("pending-state").length).toBeGreaterThan(0);
  });

  it("updates selected analysis area from the map and keeps charts following", () => {
    render(<App />);
    const cell = document.querySelector('[data-area-id="area-4"]');
    expect(cell).toBeTruthy();
    fireEvent.click(cell as Element);
    const selected = screen.getByTestId("selected-area");
    expect(selected.textContent).toContain("Analysis area 4");
    expect(selected.textContent).not.toMatch(/TEST-ONLY-/);
    expect(screen.getByTestId("chart-hourly_curve").textContent).toContain("Analysis area 4");
  });

  it("opens intervention and vulnerability questions without treatment claims", () => {
    render(<App />);
    fireEvent.click(screen.getByTestId("question-after-intervention"));
    expect(screen.getByTestId("intervention-panel").textContent).toContain("Not a treatment result");
    fireEvent.click(screen.getByTestId("question-capacity-to-cope"));
    expect(screen.getByTestId("vulnerability-panel").textContent).toContain("Not a score");
  });
});
