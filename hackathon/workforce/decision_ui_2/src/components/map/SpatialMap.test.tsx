import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { publicMapMode } from "@/data/publicSurface";
import { SpatialMap } from "./SpatialMap";

describe("SpatialMap", () => {
  it("exposes twenty-five analysis areas and reports clicks", () => {
    const onSelectArea = vi.fn();
    render(
      <SpatialMap
        mode={publicMapMode("selected_time")}
        selectedAreaId={null}
        onSelectArea={onSelectArea}
        onSelectMode={vi.fn()}
      />,
    );
    expect(document.querySelectorAll("[data-area-id]")).toHaveLength(25);
    fireEvent.click(document.querySelector('[data-area-id="area-8"]') as Element);
    expect(onSelectArea).toHaveBeenCalledWith("area-8");
    expect(screen.getByTestId("map-legend").textContent).toContain("Unit");
  });
});
