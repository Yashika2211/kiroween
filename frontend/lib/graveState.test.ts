import { describe, expect, it } from "vitest";

import { graveHref, graveState } from "./graveState";

describe("graveState", () => {
  it("only calls a grave risen when tests pass", () => {
    expect(graveState({ status: "risen", tests_passed: true })).toBe("risen");
    expect(graveState({ status: "risen", tests_passed: null })).toBe("risen");
    expect(graveState({ status: "risen", tests_passed: false })).toBe("stirring");
  });

  it("classifies the other statuses", () => {
    expect(graveState({ status: "autopsy", tests_passed: null })).toBe("working");
    expect(graveState({ status: "rejected", tests_passed: null })).toBe("failed");
    expect(graveState({ status: "autopsied", tests_passed: null })).toBe("resting");
  });

  it("links to the ritual once it has started", () => {
    expect(graveHref({ id: "a", status: "autopsied" })).toBe("/jobs/a");
    expect(graveHref({ id: "a", status: "resurrecting" })).toBe("/jobs/a/ritual");
  });
});
