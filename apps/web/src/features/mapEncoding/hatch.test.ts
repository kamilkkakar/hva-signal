import { describe, expect, it } from "vitest";
import { allHatchImages, hatchImage } from "./hatch";

describe("position hatch images", () => {
  it("emits three 16px RGBA patterns with increasing ink", () => {
    const images = allHatchImages();
    expect(images.map((image) => image.id)).toEqual([
      "hva-pos-hatch-low",
      "hva-pos-hatch-mid",
      "hva-pos-hatch-high",
    ]);
    const inkCounts = images.map((image) => {
      expect(image.width).toBe(16);
      expect(image.height).toBe(16);
      expect(image.data).toHaveLength(16 * 16 * 4);
      let ink = 0;
      for (let index = 3; index < image.data.length; index += 4) {
        if (image.data[index] > 0) {
          ink += 1;
        }
      }
      return ink;
    });
    expect(inkCounts[0]).toBeGreaterThan(0);
    expect(inkCounts[1]).toBeGreaterThan(inkCounts[0] ?? 0);
    expect(inkCounts[2]).toBeGreaterThan(inkCounts[1] ?? 0);
    expect(hatchImage("low").data[3]).toBeGreaterThan(0);
  });
});
