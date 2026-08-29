import { afterEach, describe, expect, it, vi } from "vitest";
import {
  PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL,
  phoenixAoiLocalAnalysisTime,
  phoenixAoiLocalDatetimeLocalValue,
} from "./phoenixAoiLocalTime";

describe("phoenix AOI-local analysis time", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults the demo control to 2022-07-01 03:00", () => {
    expect(PHOENIX_DEMO_DEFAULT_DATETIME_LOCAL).toBe("2022-07-01T03:00");
  });

  it("submits 2022-07-01 as naive 03:00 AOI-local, not a UTC ISO string", () => {
    expect(phoenixAoiLocalAnalysisTime("2022-07-01T03:00")).toBe(
      "2022-07-01T03:00:00",
    );
    expect(phoenixAoiLocalAnalysisTime("2022-07-01T03:00")).not.toMatch(/Z$/);
    expect(phoenixAoiLocalAnalysisTime("2022-07-01T03:00")).not.toMatch(
      /[+-]\d{2}:\d{2}$/,
    );
  });

  it("submits a selected 2022-06-30 date as naive 03:00 AOI-local", () => {
    expect(phoenixAoiLocalAnalysisTime("2022-06-30T03:00")).toBe(
      "2022-06-30T03:00:00",
    );
  });

  it("keeps the selected calendar date when the control time is not 03:00", () => {
    expect(phoenixAoiLocalAnalysisTime("2022-07-01T15:00")).toBe(
      "2022-07-01T03:00:00",
    );
    expect(phoenixAoiLocalDatetimeLocalValue("2022-06-30T18:45")).toBe(
      "2022-06-30T03:00",
    );
  });

  it("does not shift the Phoenix calendar date via Date/toISOString", () => {
    vi.spyOn(globalThis, "Date").mockImplementation(() => {
      throw new Error("Date must not be used for AOI-local analysis time");
    });
    expect(phoenixAoiLocalAnalysisTime("2022-07-01T03:00")).toBe(
      "2022-07-01T03:00:00",
    );
    expect(phoenixAoiLocalAnalysisTime("2022-06-30T03:00")).toBe(
      "2022-06-30T03:00:00",
    );
  });

  it("is stable under America/New_York and Pacific/Auckland Date timezone behavior", () => {
    const shifts: Record<string, (isoDate: string, hour: number) => Date> = {
      "America/New_York": (isoDate, hour) => {
        const utcHour = hour + 4;
        return new Date(`${isoDate}T${String(utcHour).padStart(2, "0")}:00:00.000Z`);
      },
      "Pacific/Auckland": (isoDate, hour) => {
        const utcHour = hour - 12;
        const day = utcHour < 0 ? "2022-06-30" : isoDate;
        const wrapped = utcHour < 0 ? utcHour + 24 : utcHour;
        return new Date(`${day}T${String(wrapped).padStart(2, "0")}:00:00.000Z`);
      },
    };

    for (const [zone, factory] of Object.entries(shifts)) {
      vi.spyOn(globalThis, "Date").mockImplementation(((value?: string) => {
        if (typeof value === "string" && value.startsWith("2022-07-01T03:00")) {
          return factory("2022-07-01", 3);
        }
        return factory("2022-07-01", 0);
      }) as unknown as DateConstructor);

      expect(
        phoenixAoiLocalAnalysisTime("2022-07-01T03:00"),
        zone,
      ).toBe("2022-07-01T03:00:00");
      vi.restoreAllMocks();
    }
  });

  it("rejects an input that is not a calendar date", () => {
    expect(() => phoenixAoiLocalAnalysisTime("not-a-date")).toThrow(
      /analysis time is invalid/i,
    );
  });
});
