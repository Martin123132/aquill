export type SubtitleCue = {
  index: number;
  start: number;
  end: number;
  text: string;
};

export type SubtitleQualityProfile = {
  maxCharsPerLine: number;
  maxLines: number;
  maxCps: number;
  minDuration: number;
  maxDuration: number;
};

export type SubtitleIssueCode =
  | "empty"
  | "long-line"
  | "too-many-lines"
  | "fast-reading"
  | "short-duration"
  | "long-duration";

export type SubtitleIssue = {
  code: SubtitleIssueCode;
  message: string;
};

export type SubtitleCueQuality = {
  index: number;
  duration: number;
  charactersPerSecond: number;
  lineCount: number;
  longestLine: number;
  issues: SubtitleIssue[];
};

export type SubtitleQualityReport = {
  cues: SubtitleCueQuality[];
  warningCueCount: number;
  issueCount: number;
};

export const DEFAULT_SUBTITLE_QUALITY_PROFILE: SubtitleQualityProfile = {
  maxCharsPerLine: 42,
  maxLines: 2,
  maxCps: 20,
  minDuration: 1,
  maxDuration: 7
};

export function analyseSubtitleCues(
  cues: SubtitleCue[],
  profile: SubtitleQualityProfile
): SubtitleQualityReport {
  const reports = cues.map((cue) => analyseSubtitleCue(cue, profile));
  return {
    cues: reports,
    warningCueCount: reports.filter((cue) => cue.issues.length > 0).length,
    issueCount: reports.reduce((total, cue) => total + cue.issues.length, 0)
  };
}

export function analyseSubtitleCue(
  cue: SubtitleCue,
  profile: SubtitleQualityProfile
): SubtitleCueQuality {
  const duration = Math.max(0, cue.end - cue.start);
  const normalizedText = cue.text.replace(/\s+/g, " ").trim();
  const lines = cue.text.split(/\r?\n/).map((line) => line.trim());
  const lineLengths = lines.map((line) => line.length);
  const longestLine = Math.max(0, ...lineLengths);
  const charactersPerSecond = duration > 0 ? normalizedText.length / duration : normalizedText.length > 0 ? Infinity : 0;
  const issues: SubtitleIssue[] = [];

  if (!normalizedText) {
    issues.push({ code: "empty", message: "Cue is empty" });
  }
  if (longestLine > profile.maxCharsPerLine) {
    issues.push({
      code: "long-line",
      message: `${longestLine} characters on one line (limit ${profile.maxCharsPerLine})`
    });
  }
  if (lines.length > profile.maxLines) {
    issues.push({
      code: "too-many-lines",
      message: `${lines.length} lines (limit ${profile.maxLines})`
    });
  }
  if (charactersPerSecond > profile.maxCps) {
    issues.push({
      code: "fast-reading",
      message: `${formatDecimal(charactersPerSecond)} CPS (limit ${formatDecimal(profile.maxCps)})`
    });
  }
  if (duration < profile.minDuration) {
    issues.push({
      code: "short-duration",
      message: `${formatDecimal(duration)}s cue (minimum ${formatDecimal(profile.minDuration)}s)`
    });
  }
  if (duration > profile.maxDuration) {
    issues.push({
      code: "long-duration",
      message: `${formatDecimal(duration)}s cue (maximum ${formatDecimal(profile.maxDuration)}s)`
    });
  }

  return {
    index: cue.index,
    duration,
    charactersPerSecond,
    lineCount: lines.length,
    longestLine,
    issues
  };
}

export function wrapSubtitleText(text: string, maxCharsPerLine: number) {
  const words = text.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  if (words.length === 0) return "";

  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (current && candidate.length > maxCharsPerLine) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) lines.push(current);
  return lines.join("\n");
}

function formatDecimal(value: number) {
  return Number.isFinite(value) ? value.toFixed(1) : "infinite";
}
