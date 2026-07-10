import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const STORAGE = {
  project_root: "D:\\revenge-tour\\transcriber",
  inputs_dir: "D:\\revenge-tour\\transcriber\\inputs",
  outputs_dir: "D:\\revenge-tour\\transcriber\\outputs",
  models_dir: "D:\\revenge-tour\\transcriber\\models",
  data_dir: "D:\\revenge-tour\\transcriber\\data",
  tmp_dir: "D:\\revenge-tour\\transcriber\\tmp",
  cache_dir: "D:\\revenge-tour\\transcriber\\cache"
};

const TRANSCRIPT = {
  source: STORAGE.inputs_dir + "\\meeting.wav",
  language: "en",
  duration: 8,
  text: "First rough line. Second rough line.",
  segments: [
    { index: 1, start: 0, end: 4, text: "First rough line." },
    { index: 2, start: 4, end: 8, text: "Second rough line." }
  ]
};

function makeJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-1",
    file_name: "meeting.wav",
    output_dir: STORAGE.outputs_dir + "\\meeting-job",
    status: "completed",
    model: "small",
    language: "en",
    device: "cpu",
    compute_type: "int8",
    task: "transcribe",
    vad_filter: true,
    keep_audio: false,
    created_at: "2026-07-10T10:00:00+00:00",
    updated_at: "2026-07-10T10:01:00+00:00",
    progress_message: "Completed.",
    started_at: "2026-07-10T10:00:05+00:00",
    completed_at: "2026-07-10T10:01:00+00:00",
    error: null,
    artifacts: {
      txt: "/api/jobs/job-1/download/txt",
      json: "/api/jobs/job-1/download/json",
      srt: "/api/jobs/job-1/download/srt",
      vtt: "/api/jobs/job-1/download/vtt"
    },
    transcript_url: "/api/jobs/job-1/transcript",
    archive_url: "/api/jobs/job-1/archive",
    has_original_transcript: false,
    can_cancel: false,
    can_retry: true,
    can_delete: true,
    can_open_output: true,
    ...overrides
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body
  } as Response;
}

function routeBaseRequests(url: string, jobs: unknown[], method = "GET") {
  if (url === "/api/jobs" && method === "GET") return jsonResponse({ jobs });
  if (url === "/api/models") return jsonResponse({ models: [] });
  if (url === "/api/system/storage") return jsonResponse(STORAGE);
  return null;
}

describe("Aquill workbench", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("edits a transcript and previews then applies known lyrics", async () => {
    const job = makeJob();
    const alignedTranscript = {
      ...TRANSCRIPT,
      text: "First known line. Second known line.",
      segments: [
        { index: 1, start: 0, end: 4, text: "First known line." },
        { index: 2, start: 4, end: 8, text: "Second known line." }
      ]
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const base = routeBaseRequests(url, [job], init?.method);
      if (base) return base;
      if (url === job.transcript_url && !init?.method) return jsonResponse(TRANSCRIPT);
      if (url === "/api/jobs/job-1/transcript" && init?.method === "PUT") {
        const request = JSON.parse(String(init.body)) as { segments: { index: number; text: string }[] };
        const edited = {
          ...TRANSCRIPT,
          text: request.segments.map((segment) => segment.text).join(" "),
          segments: TRANSCRIPT.segments.map((segment) => ({
            ...segment,
            text: request.segments.find((edit) => edit.index === segment.index)?.text ?? segment.text
          }))
        };
        return jsonResponse(edited);
      }
      if (url === "/api/jobs/job-1/lyrics/preview") {
        return jsonResponse({ line_count: 2, transcript: alignedTranscript, has_original_transcript: false });
      }
      if (url === "/api/jobs/job-1/lyrics") {
        return jsonResponse({ line_count: 2, transcript: alignedTranscript, has_original_transcript: true });
      }
      throw new Error(`Unhandled request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<App />);

    const firstSegment = await screen.findByLabelText("Transcript segment 1");
    await user.clear(firstSegment);
    await user.type(firstSegment, "Corrected first line.");
    await user.click(screen.getByRole("button", { name: "Save edits" }));
    expect(await screen.findByText("Exports regenerated")).toBeInTheDocument();

    await user.type(screen.getByTestId("lyrics-input"), "First known line.\nSecond known line.");
    await user.click(screen.getByTestId("lyrics-preview-button"));
    const preview = await screen.findByTestId("lyrics-preview");
    expect(within(preview).getByText("First known line.")).toBeInTheDocument();
    await user.click(screen.getByTestId("lyrics-align-button"));
    expect(await screen.findByText("2 timed lyric lines")).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-1/transcript",
      expect.objectContaining({ method: "PUT" })
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/jobs/job-1/lyrics",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("previews and imports an Aquill archive", async () => {
    let jobs: unknown[] = [];
    const importedJob = makeJob({ id: "imported-job", file_name: "restored.wav" });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const base = routeBaseRequests(url, jobs, init?.method);
      if (base) return base;
      if (url === "/api/jobs/import/preview") {
        return jsonResponse({
          preview: {
            archive_version: 1,
            source_job_id: "source-job",
            file_name: "restored.wav",
            model: "small",
            language: "en",
            task: "transcribe",
            artifacts: [
              { artifact: "txt", file_name: "transcript.txt", size_bytes: 10 },
              { artifact: "json", file_name: "transcript.json", size_bytes: 20 }
            ]
          }
        });
      }
      if (url === "/api/jobs/import") {
        jobs = [importedJob];
        return jsonResponse({ job: importedJob }, 201);
      }
      if (url === importedJob.transcript_url) return jsonResponse(TRANSCRIPT);
      throw new Error(`Unhandled request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("No active job");
    const archiveInput = screen.getByTestId("archive-import-input") as HTMLInputElement;
    await user.upload(archiveInput, new File(["archive"], "restored.zip", { type: "application/zip" }));

    expect(await screen.findByTestId("archive-preview")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Import" }));
    expect(await screen.findByText("Imported 4 artifacts")).toBeInTheDocument();
    expect(await screen.findAllByText("restored.wav")).not.toHaveLength(0);
  });

  it("retries a job interrupted by an app restart", async () => {
    const interrupted = makeJob({
      id: "interrupted-job",
      status: "failed",
      progress_message: "Interrupted by API restart before completion.",
      error: "Interrupted by API restart before completion.",
      artifacts: {},
      transcript_url: null,
      archive_url: null,
      can_retry: true
    });
    const queued = makeJob({
      id: "retry-job",
      status: "queued",
      progress_message: "Waiting for the transcription worker.",
      error: null,
      artifacts: {},
      transcript_url: null,
      archive_url: null,
      can_cancel: true,
      can_retry: false
    });
    let jobs = [interrupted];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const base = routeBaseRequests(url, jobs, init?.method);
      if (base) return base;
      if (url === "/api/jobs/interrupted-job/retry" && init?.method === "POST") {
        jobs = [queued, interrupted];
        return jsonResponse({ job: queued }, 202);
      }
      throw new Error(`Unhandled request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findAllByText("Interrupted by API restart before completion.")).not.toHaveLength(0);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Waiting for the transcription worker.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/jobs/interrupted-job/retry", { method: "POST" });
  });

  it("shows an API error when a selected upload is rejected", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const base = routeBaseRequests(url, [], init?.method);
      if (base) return base;
      if (url === "/api/jobs") return jsonResponse({ detail: "Unsupported media file." }, 400);
      throw new Error(`Unhandled request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("No active job");
    const mediaInput = document.querySelector('input[type="file"][accept="audio/*,video/*"]') as HTMLInputElement;
    await user.upload(mediaInput, new File(["bad"], "bad.wav", { type: "audio/wav" }));
    await user.click(screen.getByRole("button", { name: "Start job" }));
    expect(await screen.findByText("Unsupported media file.")).toBeInTheDocument();
  });
});
