import { describe, expect, it } from "vitest";

import {
  DEFAULT_SUBTITLE_QUALITY_PROFILE,
  analyseSubtitleCue,
  analyseSubtitleCues,
  wrapSubtitleText
} from "./subtitleQuality";

describe("subtitle quality", () => {
  it("reports line, speed, and duration problems per cue", () => {
    const report = analyseSubtitleCue(
      {
        index: 1,
        start: 1,
        end: 1.5,
        text: "This subtitle line is intentionally much longer than forty-two characters.\nAnd it has a third line.\nThird."
      },
      DEFAULT_SUBTITLE_QUALITY_PROFILE
    );

    expect(report.duration).toBe(0.5);
    expect(report.lineCount).toBe(3);
    expect(report.issues.map((issue) => issue.code)).toEqual([
      "long-line",
      "too-many-lines",
      "fast-reading",
      "short-duration"
    ]);
  });

  it("summarises only cues that have warnings", () => {
    const report = analyseSubtitleCues(
      [
        { index: 1, start: 0, end: 2, text: "Comfortable cue" },
        { index: 2, start: 2, end: 10, text: "This cue lasts too long" }
      ],
      DEFAULT_SUBTITLE_QUALITY_PROFILE
    );

    expect(report.warningCueCount).toBe(1);
    expect(report.issueCount).toBe(1);
    expect(report.cues[1].issues[0].code).toBe("long-duration");
  });

  it("wraps words without losing text and leaves long words visible", () => {
    expect(wrapSubtitleText("One two three four five", 10)).toBe("One two\nthree four\nfive");
    expect(wrapSubtitleText("  spaced\nwords   remain ", 20)).toBe("spaced words remain");
    expect(wrapSubtitleText("unbreakable", 5)).toBe("unbreakable");
  });
});
