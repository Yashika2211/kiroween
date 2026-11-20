import { describe, expect, it } from "vitest";

import { decayTone, plural, year, yearsSince } from "./format";

describe("format", () => {
  it("formats years and plurals", () => {
    expect(year("2013-03-12T00:00:00Z")).toBe("2013");
    expect(year(null)).toBe("?");
    expect(plural(1, "file")).toBe("1 file");
    expect(plural(1200, "line")).toBe("1,200 lines");
    expect(plural(2, "vulnerability", "vulnerabilities")).toBe("2 vulnerabilities");
  });

  it("computes years since a date", () => {
    expect(yearsSince("2016-11-20T00:00:00Z", new Date("2026-11-20T00:00:00Z"))).toBeCloseTo(10, 1);
    expect(yearsSince(null)).toBeNull();
  });

  it("darkens decay tone as score rises", () => {
    expect(decayTone(5)).not.toBe(decayTone(95));
  });
});
