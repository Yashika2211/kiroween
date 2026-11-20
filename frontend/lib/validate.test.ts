import { describe, expect, it } from "vitest";

import { parseRepo } from "./validate";

describe("parseRepo", () => {
  it.each([
    ["https://github.com/nvie/times", "nvie/times"],
    ["https://github.com/nvie/times.git", "nvie/times"],
    ["github.com/nvie/times/tree/master", "nvie/times"],
    ["git@github.com:nvie/times.git", "nvie/times"],
    ["nvie/times", "nvie/times"],
  ])("accepts %s", (raw, expected) => {
    expect(parseRepo(raw)).toBe(expected);
  });

  it.each(["", "https://gitlab.com/a/b", "https://github.com/nvie", "nvie/.."])("rejects %s", (raw) => {
    expect(parseRepo(raw)).toBeNull();
  });
});
