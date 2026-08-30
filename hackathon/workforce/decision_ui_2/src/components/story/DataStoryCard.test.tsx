import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { publicStoryCard } from "@/data/publicSurface";
import { TEST_ONLY_STORY_CARD } from "@/fixtures/story.fixture";
import { TEST_ONLY } from "@/fixtures/TEST_ONLY";
import { DataStoryCard } from "./DataStoryCard";

describe("DataStoryCard", () => {
  it("renders the public pending contract without fixture magnitudes", () => {
    render(<DataStoryCard card={publicStoryCard("season_behavior")} />);
    expect(screen.getByTestId("story-card-season_behavior")).toHaveAttribute("data-pending", "true");
    expect(screen.queryByText("+0.8")).toBeNull();
    expect(screen.getByText("Not published")).toBeTruthy();
    expect(screen.getByText("Baseline not bound")).toBeTruthy();
  });

  it("can render a TEST_ONLY fixture in isolation", () => {
    expect(TEST_ONLY_STORY_CARD.__testOnly).toBe(TEST_ONLY);
    render(<DataStoryCard card={TEST_ONLY_STORY_CARD} />);
    expect(screen.getByText("+0.8")).toBeTruthy();
    expect(screen.getByText("91 / 92 nights")).toBeTruthy();
  });
});
