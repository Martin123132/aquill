import {
  Activity,
  AlertTriangle,
  Captions,
  Check,
  Combine,
  Download,
  HardDrive,
  FileAudio,
  FileJson,
  FileText,
  FolderOpen,
  Headphones,
  Loader2,
  Mic2,
  Play,
  Radio,
  Redo2,
  RefreshCw,
  Replace,
  RotateCcw,
  Save,
  Scissors,
  Search,
  Scale,
  Trash2,
  Undo2,
  Upload,
  WrapText,
  Waves,
  XCircle
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  DEFAULT_SUBTITLE_QUALITY_PROFILE,
  analyseSubtitleCues,
  wrapSubtitleText,
  type SubtitleQualityProfile
} from "./subtitleQuality";

type JobStatus = "queued" | "extracting" | "transcribing" | "writing" | "completed" | "failed" | "cancelled";
type JobFilter = "all" | "active" | "completed" | "attention";

type Job = {
  id: string;
  file_name: string;
  output_dir: string;
  status: JobStatus;
  model: string;
  language: string | null;
  device: string;
  compute_type: string;
  task: string;
  vad_filter: boolean;
  keep_audio: boolean;
  created_at: string;
  updated_at: string;
  progress_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  artifacts: Record<string, string>;
  transcript_url: string | null;
  archive_url: string | null;
  media_url: string | null;
  has_original_transcript: boolean;
  can_cancel: boolean;
  can_retry: boolean;
  can_delete: boolean;
  can_open_output: boolean;
};

type ModelInfo = {
  name: string;
  description: string;
  downloaded: boolean;
  status: string;
  error: string | null;
  path: string;
  size_bytes: number;
};

type StorageInfo = {
  project_root: string;
  inputs_dir: string;
  outputs_dir: string;
  models_dir: string;
  data_dir: string;
  tmp_dir: string;
  cache_dir: string;
};

type Settings = {
  version: 1;
  model: string;
  language: string;
  device: string;
  computeType: string;
  task: "transcribe" | "translate";
  vadFilter: boolean;
  keepAudio: boolean;
};

type TranscriptSegment = {
  index: number;
  start: number;
  end: number;
  text: string;
};

type Transcript = {
  source: string;
  language: string | null;
  duration: number | null;
  text: string;
  segments: TranscriptSegment[];
};

type ArchivePreviewArtifact = {
  artifact: string;
  file_name: string;
  size_bytes: number;
};

type ArchivePreview = {
  archive_version: number;
  source_job_id: string;
  file_name: string;
  model: string;
  language: string | null;
  task: string;
  artifacts: ArchivePreviewArtifact[];
};

type LyricsAlignmentPayload = {
  line_count: number;
  transcript: Transcript;
  has_original_transcript: boolean;
};

type LyricsRestorePayload = {
  restored_artifacts: string[];
  transcript: Transcript;
  has_original_transcript: boolean;
};

type PresetMode = "standard" | "song";

const MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large-v3"];
const COMPUTE_OPTIONS = ["int8", "float16", "float32"];
const DEVICE_OPTIONS = ["auto", "cpu", "cuda"];
const SETTINGS_KEY = "aquill-settings-v1";
const SUBTITLE_QUALITY_KEY = "aquill-subtitle-quality-v1";
const SUBTITLE_PROFILE_LIMITS: Record<keyof SubtitleQualityProfile, readonly [number, number]> = {
  maxCharsPerLine: [20, 80],
  maxLines: [1, 4],
  maxCps: [8, 40],
  minDuration: [0.2, 5],
  maxDuration: [1, 15]
};
const DEFAULT_SETTINGS: Settings = {
  version: 1,
  model: "base",
  language: "en",
  device: "auto",
  computeType: "int8",
  task: "transcribe",
  vadFilter: true,
  keepAudio: false
};
const ARTIFACT_LABELS: Record<string, string> = {
  txt: "TXT",
  json: "JSON",
  srt: "SRT",
  vtt: "VTT",
  audio: "WAV"
};
const STORAGE_LABELS: Record<keyof StorageInfo, string> = {
  project_root: "Project",
  inputs_dir: "Inputs",
  outputs_dir: "Outputs",
  models_dir: "Models",
  data_dir: "Database",
  tmp_dir: "Temp",
  cache_dir: "Cache"
};
const ZIP_MIME_TYPES = new Set(["application/zip", "application/x-zip-compressed", ""]);
const JOB_FILTERS: { key: JobFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "completed", label: "Done" },
  { key: "attention", label: "Review" }
];
const ACTIVE_JOB_STATUSES = new Set<JobStatus>(["queued", "extracting", "transcribing", "writing"]);
const ATTENTION_JOB_STATUSES = new Set<JobStatus>(["failed", "cancelled"]);

function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [storageInfo, setStorageInfo] = useState<StorageInfo | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [draftSegments, setDraftSegments] = useState<TranscriptSegment[]>([]);
  const [undoStack, setUndoStack] = useState<TranscriptSegment[][]>([]);
  const [redoStack, setRedoStack] = useState<TranscriptSegment[][]>([]);
  const [transcriptSearch, setTranscriptSearch] = useState("");
  const [transcriptReplacement, setTranscriptReplacement] = useState("");
  const [editorStatus, setEditorStatus] = useState<string | null>(null);
  const [subtitleProfile, setSubtitleProfile] = useState<SubtitleQualityProfile>(() => loadSubtitleQualityProfile());
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [audioStatus, setAudioStatus] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingTranscript, setIsSavingTranscript] = useState(false);
  const [isRefreshingModels, setIsRefreshingModels] = useState(false);
  const [isImportingArchive, setIsImportingArchive] = useState(false);
  const [isPreviewingArchive, setIsPreviewingArchive] = useState(false);
  const [pendingArchiveFile, setPendingArchiveFile] = useState<File | null>(null);
  const [archivePreview, setArchivePreview] = useState<ArchivePreview | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [archiveStatus, setArchiveStatus] = useState<string | null>(null);
  const [lyricsDraft, setLyricsDraft] = useState("");
  const [lyricsPreview, setLyricsPreview] = useState<Transcript | null>(null);
  const [lyricsStatus, setLyricsStatus] = useState<string | null>(null);
  const [isAligningLyrics, setIsAligningLyrics] = useState(false);
  const [isPreviewingLyrics, setIsPreviewingLyrics] = useState(false);
  const [isRestoringOriginal, setIsRestoringOriginal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobFilter, setJobFilter] = useState<JobFilter>("all");
  const [jobSearch, setJobSearch] = useState("");
  const [settings, setSettings] = useState<Settings>(() => loadSettings());
  const [activePreset, setActivePreset] = useState<PresetMode>("standard");
  const editBaselineRef = useRef<TranscriptSegment[] | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const segmentCaretsRef = useRef(new Map<number, number>());
  const segmentTextareasRef = useRef(new Map<number, HTMLTextAreaElement>());
  const searchCursorRef = useRef({ segmentPosition: 0, offset: 0 });

  const activeJob = useMemo(
    () => jobs.find((job) => job.id === activeJobId) ?? jobs[0] ?? null,
    [jobs, activeJobId]
  );
  const jobFilterCounts = useMemo(() => {
    const counts: Record<JobFilter, number> = {
      all: jobs.length,
      active: 0,
      completed: 0,
      attention: 0
    };
    for (const job of jobs) {
      if (ACTIVE_JOB_STATUSES.has(job.status)) counts.active += 1;
      if (job.status === "completed") counts.completed += 1;
      if (ATTENTION_JOB_STATUSES.has(job.status)) counts.attention += 1;
    }
    return counts;
  }, [jobs]);
  const filteredJobs = useMemo(() => {
    const query = jobSearch.trim().toLowerCase();
    return jobs.filter((job) => {
      const matchesFilter =
        jobFilter === "all" ||
        (jobFilter === "active" && ACTIVE_JOB_STATUSES.has(job.status)) ||
        (jobFilter === "completed" && job.status === "completed") ||
        (jobFilter === "attention" && ATTENTION_JOB_STATUSES.has(job.status));
      if (!matchesFilter) return false;
      if (!query) return true;
      return [job.file_name, job.status, job.progress_message ?? "", job.output_dir]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }, [jobFilter, jobSearch, jobs]);
  const transcriptIsDirty = useMemo(() => {
    if (!transcript) return false;
    return !segmentsEqual(draftSegments, transcript.segments);
  }, [draftSegments, transcript]);
  const transcriptStructureIsDirty = useMemo(() => {
    if (!transcript) return false;
    return !segmentStructureEqual(draftSegments, transcript.segments);
  }, [draftSegments, transcript]);
  const transcriptTimingError = useMemo(
    () => (transcriptStructureIsDirty ? validateSegmentTimings(draftSegments, transcript?.duration ?? null) : null),
    [draftSegments, transcript?.duration, transcriptStructureIsDirty]
  );
  const subtitleQuality = useMemo(
    () => analyseSubtitleCues(draftSegments, subtitleProfile),
    [draftSegments, subtitleProfile]
  );
  const activeAudioSegmentIndex = useMemo(
    () =>
      activeJob?.media_url
        ? draftSegments.find(
            (segment) => audioCurrentTime >= segment.start && audioCurrentTime < segment.end
          )?.index ?? null
        : null,
    [activeJob?.media_url, audioCurrentTime, draftSegments]
  );

  useEffect(() => {
    void refreshJobs();
    void refreshModels();
    void refreshStorage();
    const timer = window.setInterval(refreshJobs, 1600);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    window.localStorage.setItem(SUBTITLE_QUALITY_KEY, JSON.stringify(subtitleProfile));
  }, [subtitleProfile]);

  useEffect(() => {
    setAudioCurrentTime(0);
    setAudioStatus(null);
  }, [activeJob?.id, activeJob?.media_url]);

  useEffect(() => {
    if (!activeJob || activeJob.status !== "completed" || !activeJob.transcript_url) {
      setEditorTranscript(null);
      setSaveStatus(null);
      setLyricsStatus(null);
      setLyricsPreview(null);
      return;
    }
    void loadTranscript(activeJob.transcript_url);
  }, [activeJob?.id, activeJob?.status, activeJob?.transcript_url]);

  function setEditorTranscript(payload: Transcript | null, resetHistory = true) {
    setTranscript(payload);
    setDraftSegments(payload ? cloneSegments(payload.segments) : []);
    editBaselineRef.current = null;
    segmentCaretsRef.current.clear();
    searchCursorRef.current = { segmentPosition: 0, offset: 0 };
    setEditorStatus(null);
    if (resetHistory) {
      setUndoStack([]);
      setRedoStack([]);
      setTranscriptSearch("");
      setTranscriptReplacement("");
    }
  }

  async function refreshJobs() {
    try {
      const response = await fetch("/api/jobs");
      if (!response.ok) return;
      const payload = (await response.json()) as { jobs: Job[] };
      setJobs(payload.jobs);
      setActiveJobId((current) => current ?? payload.jobs[0]?.id ?? null);
    } catch {
      return;
    }
  }

  async function refreshModels() {
    setIsRefreshingModels(true);
    try {
      const response = await fetch("/api/models");
      if (!response.ok) return;
      const payload = (await response.json()) as { models: ModelInfo[] };
      setModels(payload.models);
    } finally {
      setIsRefreshingModels(false);
    }
  }

  async function refreshStorage() {
    try {
      const response = await fetch("/api/system/storage");
      if (!response.ok) return;
      const payload = (await response.json()) as StorageInfo;
      setStorageInfo(payload);
    } catch {
      return;
    }
  }

  async function loadTranscript(url: string) {
    const response = await fetch(url);
    if (!response.ok) return;
    const payload = (await response.json()) as Transcript;
    setEditorTranscript(payload);
    setSaveStatus(null);
    setLyricsStatus(null);
    setLyricsPreview(null);
  }

  async function saveTranscript() {
    if (!activeJob || !transcript || !transcriptIsDirty) return;
    setIsSavingTranscript(true);
    setSaveStatus(null);

    try {
      const response = await fetch(`/api/jobs/${activeJob.id}/transcript`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: draftSegments.map((segment) =>
            transcriptStructureIsDirty
              ? {
                  index: segment.index,
                  start: segment.start,
                  end: segment.end,
                  text: segment.text
                }
              : {
                  index: segment.index,
                  text: segment.text
                }
          )
        })
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Transcript save failed.");
      }
      const payload = (await response.json()) as Transcript;
      setEditorTranscript(payload, false);
      setSaveStatus("Exports regenerated");
      await refreshJobs();
    } catch (caught) {
      setSaveStatus(caught instanceof Error ? caught.message : "Transcript save failed.");
    } finally {
      setIsSavingTranscript(false);
    }
  }

  function applyPreset(preset: PresetMode) {
    setActivePreset(preset);
    if (preset === "song") {
      setSettings((current) => ({
        ...current,
        model: "small",
        language: "en",
        device: "auto",
        computeType: "int8",
        task: "transcribe",
        vadFilter: true
      }));
    }
  }

  function updateLyricsDraft(value: string) {
    setLyricsDraft(value);
    setLyricsPreview(null);
    setLyricsStatus(null);
  }

  async function previewLyrics() {
    if (!activeJob || !transcript || !lyricsDraft.trim()) return;
    setIsPreviewingLyrics(true);
    setLyricsStatus(null);

    try {
      const response = await fetch(`/api/jobs/${activeJob.id}/lyrics/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lyrics: lyricsDraft })
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Lyrics preview failed.");
      }
      const payload = (await response.json()) as LyricsAlignmentPayload;
      setLyricsPreview(payload.transcript);
      setLyricsStatus(`${payload.line_count} timed lyric line${payload.line_count === 1 ? "" : "s"} ready`);
    } catch (caught) {
      setLyricsPreview(null);
      setLyricsStatus(caught instanceof Error ? caught.message : "Lyrics preview failed.");
    } finally {
      setIsPreviewingLyrics(false);
    }
  }

  async function alignLyrics() {
    if (!activeJob || !transcript || !lyricsDraft.trim() || !lyricsPreview) return;
    setIsAligningLyrics(true);
    setLyricsStatus(null);

    try {
      const response = await fetch(`/api/jobs/${activeJob.id}/lyrics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lyrics: lyricsDraft })
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Lyrics alignment failed.");
      }
      const payload = (await response.json()) as LyricsAlignmentPayload;
      setEditorTranscript(payload.transcript);
      setLyricsDraft("");
      setLyricsPreview(null);
      setLyricsStatus(`${payload.line_count} timed lyric line${payload.line_count === 1 ? "" : "s"}`);
      setSaveStatus("Exports regenerated");
      await refreshJobs();
    } catch (caught) {
      setLyricsStatus(caught instanceof Error ? caught.message : "Lyrics alignment failed.");
    } finally {
      setIsAligningLyrics(false);
    }
  }

  async function restoreOriginalTranscript() {
    if (!activeJob?.has_original_transcript) return;
    setIsRestoringOriginal(true);
    setSaveStatus(null);

    try {
      const response = await fetch(`/api/jobs/${activeJob.id}/transcript/restore-original`, { method: "POST" });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Original restore failed.");
      }
      const payload = (await response.json()) as LyricsRestorePayload;
      setEditorTranscript(payload.transcript);
      setLyricsDraft("");
      setLyricsPreview(null);
      setLyricsStatus(null);
      setSaveStatus(`Original restored (${payload.restored_artifacts.length})`);
      await refreshJobs();
    } catch (caught) {
      setSaveStatus(caught instanceof Error ? caught.message : "Original restore failed.");
    } finally {
      setIsRestoringOriginal(false);
    }
  }

  async function submitJob(event: FormEvent) {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      setError("Choose at least one media file first.");
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      const createdJobs: Job[] = [];
      for (const file of selectedFiles) {
        const body = new FormData();
        body.append("file", file);
        body.append("model", settings.model);
        body.append("language", settings.language.trim());
        body.append("device", settings.device);
        body.append("compute_type", settings.computeType);
        body.append("task", settings.task);
        body.append("vad_filter", String(settings.vadFilter));
        body.append("keep_audio", String(settings.keepAudio));

        const response = await fetch("/api/jobs", { method: "POST", body });
        if (!response.ok) {
          const payload = await response.json().catch(() => null);
          throw new Error(payload?.detail ?? `Job creation failed for ${file.name}.`);
        }
        const payload = (await response.json()) as { job: Job };
        createdJobs.push(payload.job);
      }
      setJobs((current) => [
        ...createdJobs,
        ...current.filter((job) => !createdJobs.some((created) => created.id === job.id))
      ]);
      setActiveJobId(createdJobs[0]?.id ?? null);
      setSelectedFiles([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Job creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function onFiles(files: FileList | null) {
    const incoming = Array.from(files ?? []);
    if (incoming.length === 0) return;
    setSelectedFiles((current) => {
      const known = new Set(current.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
      return [
        ...current,
        ...incoming.filter((file) => !known.has(`${file.name}:${file.size}:${file.lastModified}`))
      ];
    });
  }

  function updateDraftSegment(index: number, text: string) {
    captureCurrentEditUndo();
    setDraftSegments((segments) =>
      segments.map((segment) => (segment.index === index ? { ...segment, text } : segment))
    );
    setSaveStatus(null);
  }

  function updateSegmentTiming(index: number, field: "start" | "end", value: string) {
    if (value === "") return;
    const seconds = Number(value);
    if (!Number.isFinite(seconds)) return;
    captureCurrentEditUndo();
    setDraftSegments((segments) =>
      segments.map((segment) => (segment.index === index ? { ...segment, [field]: seconds } : segment))
    );
    setSaveStatus(null);
  }

  function rememberUndo(snapshot: TranscriptSegment[]) {
    const saved = cloneSegments(snapshot);
    setUndoStack((current) => {
      if (current.length > 0 && segmentsEqual(current[current.length - 1], saved)) return current;
      return [...current, saved].slice(-50);
    });
    setRedoStack([]);
  }

  function beginSegmentEdit() {
    if (!editBaselineRef.current) editBaselineRef.current = cloneSegments(draftSegments);
  }

  function captureCurrentEditUndo() {
    const baseline = editBaselineRef.current;
    editBaselineRef.current = null;
    if (baseline) rememberUndo(baseline);
  }

  function finishSegmentEdit() {
    editBaselineRef.current = null;
  }

  function applyDraftSegments(nextSegments: TranscriptSegment[], status: string) {
    const next = renumberSegments(nextSegments);
    if (segmentsEqual(next, draftSegments)) return;
    rememberUndo(draftSegments);
    setDraftSegments(next);
    segmentCaretsRef.current.clear();
    searchCursorRef.current = { segmentPosition: 0, offset: 0 };
    setEditorStatus(status);
    setSaveStatus(null);
  }

  function undoTranscriptEdit() {
    const previous = undoStack[undoStack.length - 1];
    if (!previous) return;
    editBaselineRef.current = null;
    setUndoStack((current) => current.slice(0, -1));
    setRedoStack((current) => [...current, cloneSegments(draftSegments)].slice(-50));
    setDraftSegments(cloneSegments(previous));
    setEditorStatus("Undid transcript edit");
    setSaveStatus(null);
  }

  function redoTranscriptEdit() {
    const next = redoStack[redoStack.length - 1];
    if (!next) return;
    editBaselineRef.current = null;
    setRedoStack((current) => current.slice(0, -1));
    setUndoStack((current) => [...current, cloneSegments(draftSegments)].slice(-50));
    setDraftSegments(cloneSegments(next));
    setEditorStatus("Redid transcript edit");
    setSaveStatus(null);
  }

  function splitSegment(index: number) {
    const position = draftSegments.findIndex((segment) => segment.index === index);
    const segment = draftSegments[position];
    if (!segment) return;

    const rememberedCaret = segmentCaretsRef.current.get(index);
    const splitAt =
      rememberedCaret && rememberedCaret > 0 && rememberedCaret < segment.text.length
        ? rememberedCaret
        : bestSplitPosition(segment.text);
    const before = segment.text.slice(0, splitAt).trim();
    const after = segment.text.slice(splitAt).trim();
    if (!before || !after) {
      setEditorStatus("Place the cursor between words before splitting");
      return;
    }

    const duration = segment.end - segment.start;
    if (duration <= 0.002) {
      setEditorStatus("This segment is too short to split");
      return;
    }
    const ratio = Math.min(0.9, Math.max(0.1, splitAt / segment.text.length));
    const splitTime = Math.min(
      segment.end - 0.001,
      Math.max(segment.start + 0.001, roundSeconds(segment.start + duration * ratio))
    );
    const next = [
      ...draftSegments.slice(0, position),
      { ...segment, end: splitTime, text: before },
      { ...segment, index: segment.index + 1, start: splitTime, text: after },
      ...draftSegments.slice(position + 1)
    ];
    applyDraftSegments(next, "Segment split");
  }

  function mergeSegmentWithPrevious(index: number) {
    const position = draftSegments.findIndex((segment) => segment.index === index);
    if (position <= 0) return;
    const previous = draftSegments[position - 1];
    const current = draftSegments[position];
    const merged = {
      ...previous,
      end: current.end,
      text: [previous.text.trim(), current.text.trim()].filter(Boolean).join(" ")
    };
    applyDraftSegments(
      [...draftSegments.slice(0, position - 1), merged, ...draftSegments.slice(position + 1)],
      "Segments merged"
    );
  }

  function findNextTranscriptMatch() {
    if (!transcriptSearch || draftSegments.length === 0) return;
    const query = transcriptSearch.toLocaleLowerCase();
    const cursor = searchCursorRef.current;
    const attempts = draftSegments.length + (cursor.offset > 0 ? 1 : 0);
    for (let step = 0; step < attempts; step += 1) {
      const position = (cursor.segmentPosition + step) % draftSegments.length;
      const segment = draftSegments[position];
      const offset = step === 0 ? cursor.offset : 0;
      const match = segment.text.toLocaleLowerCase().indexOf(query, offset);
      if (match < 0) continue;
      const textarea = segmentTextareasRef.current.get(segment.index);
      textarea?.focus();
      textarea?.setSelectionRange(match, match + transcriptSearch.length);
      segmentCaretsRef.current.set(segment.index, match + transcriptSearch.length);
      searchCursorRef.current = { segmentPosition: position, offset: match + transcriptSearch.length };
      setEditorStatus(`Match in segment ${segment.index}`);
      return;
    }
    searchCursorRef.current = { segmentPosition: 0, offset: 0 };
    setEditorStatus("No more matches");
  }

  function replaceAllTranscriptMatches() {
    if (!transcriptSearch) return;
    const expression = new RegExp(escapeRegularExpression(transcriptSearch), "gi");
    let replacements = 0;
    const next = draftSegments.map((segment) => ({
      ...segment,
      text: segment.text.replace(expression, () => {
        replacements += 1;
        return transcriptReplacement;
      })
    }));
    if (replacements === 0) {
      setEditorStatus("No matches to replace");
      return;
    }
    applyDraftSegments(next, `${replacements} replacement${replacements === 1 ? "" : "s"}`);
  }

  function updateSubtitleProfile(field: keyof SubtitleQualityProfile, value: number) {
    if (!Number.isFinite(value)) return;
    setSubtitleProfile((current) => {
      const [minimum, maximum] = SUBTITLE_PROFILE_LIMITS[field];
      const next = { ...current, [field]: Math.min(maximum, Math.max(minimum, value)) };
      if (field === "minDuration" && next.minDuration > next.maxDuration) {
        next.maxDuration = next.minDuration;
      }
      if (field === "maxDuration" && next.maxDuration < next.minDuration) {
        next.minDuration = next.maxDuration;
      }
      return next;
    });
  }

  function wrapAllSubtitleCues() {
    const next = draftSegments.map((segment) => ({
      ...segment,
      text: wrapSubtitleText(segment.text, subtitleProfile.maxCharsPerLine)
    }));
    if (segmentsEqual(next, draftSegments)) {
      setEditorStatus(`Cues already wrap at ${subtitleProfile.maxCharsPerLine} characters`);
      return;
    }
    applyDraftSegments(next, `Wrapped cues at ${subtitleProfile.maxCharsPerLine} characters`);
  }

  function playSubtitleCue(segment: TranscriptSegment) {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = segment.start;
    setAudioCurrentTime(segment.start);
    setAudioStatus(null);
    void audio.play().catch(() => setAudioStatus("This media format could not be played by the browser."));
  }

  function removeSelectedFile(fileToRemove: File) {
    setSelectedFiles((files) => files.filter((file) => file !== fileToRemove));
  }

  async function previewArchive(file: File | null) {
    if (!file) return;
    if (!isZipArchive(file)) {
      setPendingArchiveFile(null);
      setArchivePreview(null);
      setArchiveStatus(null);
      setError("Choose a ZIP archive exported by this app.");
      return;
    }
    setIsPreviewingArchive(true);
    setPendingArchiveFile(file);
    setArchivePreview(null);
    setArchiveStatus(`Reading ${file.name}`);
    setError(null);

    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/jobs/import/preview", { method: "POST", body });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Archive preview failed.");
      }
      const payload = (await response.json()) as { preview: ArchivePreview };
      setArchivePreview(payload.preview);
      setArchiveStatus("Archive ready to import");
    } catch (caught) {
      setPendingArchiveFile(null);
      setArchivePreview(null);
      setArchiveStatus(null);
      setError(caught instanceof Error ? caught.message : "Archive preview failed.");
    } finally {
      setIsPreviewingArchive(false);
    }
  }

  function clearArchivePreview() {
    setPendingArchiveFile(null);
    setArchivePreview(null);
    setArchiveStatus(null);
  }

  async function importArchive(file: File | null) {
    if (!file) return;
    if (!isZipArchive(file)) {
      setArchiveStatus(null);
      setError("Choose a ZIP archive exported by this app.");
      return;
    }
    setIsImportingArchive(true);
    setArchiveStatus(`Importing ${file.name}`);
    setError(null);

    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/jobs/import", { method: "POST", body });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Archive import failed.");
      }
      const payload = (await response.json()) as { job: Job };
      setJobs((current) => [payload.job, ...current.filter((job) => job.id !== payload.job.id)]);
      setActiveJobId(payload.job.id);
      const artifactCount = Object.keys(payload.job.artifacts).length;
      setArchiveStatus(`Imported ${artifactCount} artifact${artifactCount === 1 ? "" : "s"}`);
      setPendingArchiveFile(null);
      setArchivePreview(null);
      await refreshJobs();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Archive import failed.");
      setArchiveStatus(null);
    } finally {
      setIsImportingArchive(false);
    }
  }

  async function runJobAction(action: "cancel" | "retry" | "delete" | "open" | "export") {
    if (!activeJob) return;
    if (action === "delete" && !window.confirm("Delete this job and its generated files?")) return;
    if (action === "export") {
      if (activeJob.archive_url) window.location.href = activeJob.archive_url;
      return;
    }

    const method = action === "delete" ? "DELETE" : "POST";
    const suffix = action === "delete" ? "" : `/${action === "open" ? "open-output" : action}`;
    const response = await fetch(`/api/jobs/${activeJob.id}${suffix}`, { method });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setError(payload?.detail ?? `${action} failed.`);
      return;
    }
    setError(null);
    await refreshJobs();
  }

  async function runModelAction(modelName: string, action: "download" | "remove") {
    if (action === "remove" && !window.confirm(`Remove ${modelName} from local model storage?`)) return;
    const response = await fetch(`/api/models/${modelName}${action === "download" ? "/download" : ""}`, {
      method: action === "download" ? "POST" : "DELETE"
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setError(payload?.detail ?? `${action} model failed.`);
      return;
    }
    setError(null);
    await refreshModels();
  }

  return (
    <main className="app-shell">
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark">
            <Mic2 size={22} aria-hidden />
          </div>
          <div>
            <h1>Aquill</h1>
            <p>D:\revenge-tour\transcriber</p>
          </div>
        </div>

        <div className="rail-section">
          <div className="section-title">
            <Activity size={15} aria-hidden />
            Queue
          </div>
          <label className="queue-search">
            <Search size={15} aria-hidden />
            <input
              type="search"
              placeholder="Search jobs"
              value={jobSearch}
              onChange={(event) => setJobSearch(event.target.value)}
              data-testid="job-search-input"
            />
          </label>
          <div className="queue-filters" aria-label="Job filters">
            {JOB_FILTERS.map((filter) => (
              <button
                key={filter.key}
                className={jobFilter === filter.key ? "active" : ""}
                type="button"
                onClick={() => setJobFilter(filter.key)}
                data-testid={`job-filter-${filter.key}`}
              >
                <span>{filter.label}</span>
                <strong>{jobFilterCounts[filter.key]}</strong>
              </button>
            ))}
          </div>
          <div className="job-list">
            {jobs.length === 0 ? (
              <div className="empty-row">No jobs yet</div>
            ) : filteredJobs.length === 0 ? (
              <div className="empty-row">No jobs match this view</div>
            ) : (
              filteredJobs.map((job) => (
                <button
                  key={job.id}
                  className={`job-row ${job.id === activeJob?.id ? "selected" : ""}`}
                  onClick={() => setActiveJobId(job.id)}
                  type="button"
                  data-testid="job-row"
                  data-job-status={job.status}
                >
                  <span className={`status-dot ${job.status}`} />
                  <span>
                    <strong>{job.file_name}</strong>
                    <small>{job.progress_message ?? job.status}</small>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="workspace-label">Local workbench</p>
            <h2>Transcribe media</h2>
          </div>
          <button className="ghost-button" type="button" onClick={refreshJobs} title="Refresh queue">
            <RefreshCw size={17} aria-hidden />
            Refresh
          </button>
        </header>

        <div className="work-grid">
          <form className="panel intake-panel" onSubmit={submitJob}>
            <label
              className={`drop-zone ${isDragging ? "dragging" : ""}`}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                onFiles(event.dataTransfer.files);
              }}
            >
              <input multiple type="file" accept="audio/*,video/*" onChange={(event) => onFiles(event.target.files)} />
              <span className="drop-icon">
                <Upload size={24} aria-hidden />
              </span>
              <strong>{selectedFiles.length > 0 ? `${selectedFiles.length} file${selectedFiles.length === 1 ? "" : "s"} selected` : "Drop media here"}</strong>
              <small>{selectedFiles.length > 0 ? `${formatBytes(totalSelectedBytes(selectedFiles))} total` : "Audio or video"}</small>
            </label>

            {selectedFiles.length > 0 ? (
              <div className="selected-files">
                {selectedFiles.map((file) => (
                  <button key={`${file.name}:${file.size}:${file.lastModified}`} type="button" onClick={() => removeSelectedFile(file)}>
                    <XCircle size={15} aria-hidden />
                    <span>{file.name}</span>
                    <small>{formatBytes(file.size)}</small>
                  </button>
                ))}
              </div>
            ) : null}

            <div className="preset-row" aria-label="Transcription presets">
              <button
                type="button"
                className={activePreset === "standard" ? "active" : ""}
                onClick={() => applyPreset("standard")}
                data-testid="preset-standard-button"
              >
                <Mic2 size={16} aria-hidden />
                Standard
              </button>
              <button
                type="button"
                className={activePreset === "song" ? "active" : ""}
                onClick={() => applyPreset("song")}
                data-testid="preset-song-button"
              >
                <Captions size={16} aria-hidden />
                Song
              </button>
            </div>
            {activePreset === "song" ? <p className="preset-note">Song transcription is approximate.</p> : null}

            <div className="control-grid">
              <SelectField label="Model" value={settings.model} onChange={(model) => setSettings((current) => ({ ...current, model }))} options={MODEL_OPTIONS} />
              <TextField label="Language" value={settings.language} onChange={(language) => setSettings((current) => ({ ...current, language }))} placeholder="auto" />
              <SelectField label="Device" value={settings.device} onChange={(device) => setSettings((current) => ({ ...current, device }))} options={DEVICE_OPTIONS} />
              <SelectField label="Compute" value={settings.computeType} onChange={(computeType) => setSettings((current) => ({ ...current, computeType }))} options={COMPUTE_OPTIONS} />
            </div>

            <div className="segmented">
              <button
                type="button"
                className={settings.task === "transcribe" ? "active" : ""}
                onClick={() => setSettings((current) => ({ ...current, task: "transcribe" }))}
              >
                <Captions size={16} aria-hidden />
                Transcribe
              </button>
              <button
                type="button"
                className={settings.task === "translate" ? "active" : ""}
                onClick={() => setSettings((current) => ({ ...current, task: "translate" }))}
              >
                <Waves size={16} aria-hidden />
                Translate
              </button>
            </div>

            <div className="check-row">
              <label>
                <input type="checkbox" checked={settings.vadFilter} onChange={(event) => setSettings((current) => ({ ...current, vadFilter: event.target.checked }))} />
                Voice filter
              </label>
              <label>
                <input type="checkbox" checked={settings.keepAudio} onChange={(event) => setSettings((current) => ({ ...current, keepAudio: event.target.checked }))} />
                Keep WAV
              </label>
            </div>

            {error ? <p className="error-text">{error}</p> : null}

            <button className="primary-button" disabled={isSubmitting || selectedFiles.length === 0} type="submit">
              {isSubmitting ? <Loader2 className="spin" size={18} aria-hidden /> : <Play size={18} aria-hidden />}
              Start {selectedFiles.length > 1 ? `${selectedFiles.length} jobs` : "job"}
            </button>

            <div className="archive-tools">
              <label className={`secondary-button archive-import ${isImportingArchive || isPreviewingArchive ? "disabled" : ""}`} data-testid="archive-import-label">
                {isPreviewingArchive ? <Loader2 className="spin" size={16} aria-hidden /> : <Upload size={16} aria-hidden />}
                Choose ZIP
                <input
                  data-testid="archive-import-input"
                  type="file"
                  accept=".zip,application/zip"
                  disabled={isImportingArchive || isPreviewingArchive}
                  onChange={(event) => {
                    void previewArchive(event.target.files?.[0] ?? null);
                    event.currentTarget.value = "";
                  }}
                />
              </label>
              {archiveStatus ? <span className="save-state">{archiveStatus}</span> : null}
              {archivePreview && pendingArchiveFile ? (
                <div className="archive-preview" data-testid="archive-preview">
                  <div>
                    <strong>{archivePreview.file_name}</strong>
                    <span>
                      v{archivePreview.archive_version} / {archivePreview.model} / {archivePreview.language ?? "auto"} / {archivePreview.task}
                    </span>
                    <small>
                      {archivePreview.artifacts.map((artifact) => artifact.artifact.toUpperCase()).join(", ")} / source {archivePreview.source_job_id.slice(0, 8)}
                    </small>
                  </div>
                  <div className="archive-preview-actions">
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={isImportingArchive}
                      onClick={() => void importArchive(pendingArchiveFile)}
                    >
                      {isImportingArchive ? <Loader2 className="spin" size={16} aria-hidden /> : <Upload size={16} aria-hidden />}
                      Import
                    </button>
                    <button className="ghost-button" type="button" disabled={isImportingArchive} onClick={clearArchivePreview}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </form>

          <section className="panel status-panel">
            <PanelHeading icon={<Radio size={17} aria-hidden />} title="Active job" />
            {activeJob ? (
              <>
                <div className="job-summary">
                  <div>
                    <span className={`large-status ${activeJob.status}`}>
                      {jobStatusIcon(activeJob.status)}
                    </span>
                  </div>
                  <div>
                    <h3>{activeJob.file_name}</h3>
                    <p>{activeJob.output_dir}</p>
                  </div>
                </div>
                <p className={`progress-message ${activeJob.status}`}>
                  {activeJob.progress_message ?? statusLabel(activeJob.status)}
                </p>
                <div className="job-metrics">
                  <Metric label="Status" value={statusLabel(activeJob.status)} />
                  <Metric label="Started" value={formatDateTime(activeJob.started_at)} />
                  <Metric label="Elapsed" value={formatJobRuntime(activeJob)} />
                </div>
                <Progress status={activeJob.status} />
                {activeJob.error ? <p className="error-text">{activeJob.error}</p> : null}
                <div className="job-actions">
                  <button type="button" onClick={() => runJobAction("open")} disabled={!activeJob.can_open_output}>
                    <FolderOpen size={15} aria-hidden />
                    Open
                  </button>
                  <button type="button" onClick={() => runJobAction("retry")} disabled={!activeJob.can_retry}>
                    <RotateCcw size={15} aria-hidden />
                    Retry
                  </button>
                  <button type="button" onClick={() => runJobAction("cancel")} disabled={!activeJob.can_cancel}>
                    <XCircle size={15} aria-hidden />
                    Cancel
                  </button>
                  <button type="button" onClick={() => runJobAction("delete")} disabled={!activeJob.can_delete}>
                    <Trash2 size={15} aria-hidden />
                    Delete
                  </button>
                  <button type="button" onClick={() => runJobAction("export")} disabled={!activeJob.archive_url} data-testid="job-export-button">
                    <Download size={15} aria-hidden />
                    Export
                  </button>
                </div>
                <div className="artifact-grid">
                  {Object.entries(ARTIFACT_LABELS).map(([key, label]) => (
                    <a
                      key={key}
                      className={`artifact-button ${activeJob.artifacts[key] ? "" : "disabled"}`}
                      href={activeJob.artifacts[key] ?? "#"}
                      aria-disabled={!activeJob.artifacts[key]}
                    >
                      {artifactIcon(key)}
                      {label}
                    </a>
                  ))}
                </div>
              </>
            ) : (
              <div className="empty-state">
                <FolderOpen size={28} aria-hidden />
                <span>No active job</span>
              </div>
            )}
          </section>
        </div>

        <section className="panel model-panel">
          <div className="transcript-header">
            <PanelHeading icon={<HardDrive size={17} aria-hidden />} title="Model manager" />
            <button className="ghost-button" type="button" onClick={refreshModels}>
              {isRefreshingModels ? <Loader2 className="spin" size={16} aria-hidden /> : <RefreshCw size={16} aria-hidden />}
              Models
            </button>
          </div>
          <div className="model-grid">
            {models.map((modelInfo) => (
              <div className="model-row" key={modelInfo.name}>
                <div>
                  <strong>{modelInfo.name}</strong>
                  <span>{modelInfo.description}</span>
                  {modelInfo.error ? <small>{modelInfo.error}</small> : null}
                </div>
                <div className="model-meta">
                  <span>{modelInfo.status}</span>
                  <strong>{formatBytes(modelInfo.size_bytes)}</strong>
                </div>
                <div className="model-actions">
                  <button type="button" disabled={modelInfo.status === "downloading"} onClick={() => runModelAction(modelInfo.name, "download")}>
                    <Download size={15} aria-hidden />
                    Download
                  </button>
                  <button type="button" disabled={!modelInfo.downloaded || modelInfo.status === "downloading"} onClick={() => runModelAction(modelInfo.name, "remove")}>
                    <Trash2 size={15} aria-hidden />
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel storage-panel">
          <div className="transcript-header">
            <PanelHeading icon={<HardDrive size={17} aria-hidden />} title="Storage" />
            <span className="storage-badge">D-drive local</span>
          </div>
          {storageInfo ? (
            <div className="storage-grid">
              {(Object.entries(STORAGE_LABELS) as [keyof StorageInfo, string][]).map(([key, label]) => (
                <div className="storage-row" key={key}>
                  <span>{label}</span>
                  <code>{storageInfo[key]}</code>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-transcript">Storage paths will appear when the API is available.</div>
          )}
        </section>

        <section className="panel license-panel" data-testid="license-panel">
          <PanelHeading icon={<Scale size={17} aria-hidden />} title="License" />
          <div className="license-copy">
            <strong>PolyForm Noncommercial License 1.0.0</strong>
            <p>
              Free for personal, local, hobby, research, testing, educational, charitable, public-interest, and other noncommercial use.
            </p>
            <p>
              Commercial hosting, resale, paid subscription use, ad-supported service use, or inclusion in a paid transcription, subtitle, file conversion, or media automation service needs a separate commercial license.
            </p>
          </div>
        </section>

        <section className="panel transcript-panel">
          <div className="transcript-header">
            <PanelHeading icon={<FileText size={17} aria-hidden />} title="Transcript" />
            <div className="transcript-actions">
              {saveStatus ? <span className="save-state">{saveStatus}</span> : null}
              <button
                className="ghost-button"
                data-testid="restore-original-button"
                disabled={!activeJob?.has_original_transcript || isRestoringOriginal}
                onClick={restoreOriginalTranscript}
                type="button"
              >
                {isRestoringOriginal ? <Loader2 className="spin" size={16} aria-hidden /> : <RotateCcw size={16} aria-hidden />}
                Restore original
              </button>
              <button
                className="secondary-button"
                disabled={!transcriptIsDirty || isSavingTranscript || Boolean(transcriptTimingError)}
                onClick={saveTranscript}
                type="button"
              >
                {isSavingTranscript ? <Loader2 className="spin" size={16} aria-hidden /> : <Save size={16} aria-hidden />}
                Save edits
              </button>
            </div>
          </div>
          {transcript ? (
            <>
              <div className="transcript-editor-toolbar" data-testid="transcript-editor-toolbar">
                <div className="history-actions">
                  <button
                    className="ghost-button icon-button"
                    type="button"
                    title="Undo transcript edit"
                    aria-label="Undo transcript edit"
                    disabled={undoStack.length === 0}
                    onClick={undoTranscriptEdit}
                  >
                    <Undo2 size={16} aria-hidden />
                  </button>
                  <button
                    className="ghost-button icon-button"
                    type="button"
                    title="Redo transcript edit"
                    aria-label="Redo transcript edit"
                    disabled={redoStack.length === 0}
                    onClick={redoTranscriptEdit}
                  >
                    <Redo2 size={16} aria-hidden />
                  </button>
                </div>
                <label className="editor-search-field">
                  <span>Find</span>
                  <input
                    aria-label="Find in transcript"
                    value={transcriptSearch}
                    onChange={(event) => {
                      setTranscriptSearch(event.target.value);
                      searchCursorRef.current = { segmentPosition: 0, offset: 0 };
                      setEditorStatus(null);
                    }}
                  />
                </label>
                <label className="editor-search-field">
                  <span>Replace</span>
                  <input
                    aria-label="Replace in transcript"
                    value={transcriptReplacement}
                    onChange={(event) => setTranscriptReplacement(event.target.value)}
                  />
                </label>
                <button
                  className="ghost-button editor-command"
                  type="button"
                  disabled={!transcriptSearch}
                  onClick={findNextTranscriptMatch}
                >
                  <Search size={16} aria-hidden />
                  Find next
                </button>
                <button
                  className="secondary-button editor-command"
                  type="button"
                  disabled={!transcriptSearch}
                  onClick={replaceAllTranscriptMatches}
                >
                  <Replace size={16} aria-hidden />
                  Replace all
                </button>
                {transcriptTimingError || editorStatus ? (
                  <span className={`editor-status ${transcriptTimingError ? "error" : ""}`}>
                    {transcriptTimingError ?? editorStatus}
                  </span>
                ) : null}
              </div>
              <div className="subtitle-audio-tool" data-testid="subtitle-audio-tool">
                <div className="subtitle-audio-heading">
                  <Headphones size={17} aria-hidden />
                  <strong>Audio preview</strong>
                  <span>
                    {activeAudioSegmentIndex ? `Cue ${activeAudioSegmentIndex}` : "No active cue"} / {formatPreciseTime(audioCurrentTime)}
                  </span>
                </div>
                {activeJob?.media_url ? (
                  <audio
                    key={activeJob.media_url}
                    ref={audioRef}
                    controls
                    preload="metadata"
                    src={activeJob.media_url}
                    onTimeUpdate={(event) => setAudioCurrentTime(event.currentTarget.currentTime)}
                    onSeeked={(event) => setAudioCurrentTime(event.currentTarget.currentTime)}
                    onCanPlay={() => setAudioStatus(null)}
                    onError={() => setAudioStatus("This local media format is not playable in the browser.")}
                  />
                ) : (
                  <span className="audio-unavailable">No local preview media</span>
                )}
                {audioStatus ? <span className="audio-status">{audioStatus}</span> : null}
              </div>
              <div className="subtitle-quality-tool" data-testid="subtitle-quality-tool">
                <div className={`quality-summary ${subtitleQuality.warningCueCount > 0 ? "warning" : "clear"}`}>
                  {subtitleQuality.warningCueCount > 0 ? (
                    <AlertTriangle size={18} aria-hidden />
                  ) : (
                    <Check size={18} aria-hidden />
                  )}
                  <span>
                    <strong>
                      {subtitleQuality.warningCueCount > 0
                        ? `${subtitleQuality.warningCueCount} cue${subtitleQuality.warningCueCount === 1 ? "" : "s"} to review`
                        : "All cues clear"}
                    </strong>
                    <small>{subtitleQuality.issueCount} warning{subtitleQuality.issueCount === 1 ? "" : "s"}</small>
                  </span>
                </div>
                <div className="quality-controls">
                  <QualityNumberField
                    label="Chars / line"
                    value={subtitleProfile.maxCharsPerLine}
                    min={SUBTITLE_PROFILE_LIMITS.maxCharsPerLine[0]}
                    max={SUBTITLE_PROFILE_LIMITS.maxCharsPerLine[1]}
                    step={1}
                    onChange={(value) => updateSubtitleProfile("maxCharsPerLine", value)}
                  />
                  <QualityNumberField
                    label="Max lines"
                    value={subtitleProfile.maxLines}
                    min={SUBTITLE_PROFILE_LIMITS.maxLines[0]}
                    max={SUBTITLE_PROFILE_LIMITS.maxLines[1]}
                    step={1}
                    onChange={(value) => updateSubtitleProfile("maxLines", value)}
                  />
                  <QualityNumberField
                    label="Max CPS"
                    value={subtitleProfile.maxCps}
                    min={SUBTITLE_PROFILE_LIMITS.maxCps[0]}
                    max={SUBTITLE_PROFILE_LIMITS.maxCps[1]}
                    step={1}
                    onChange={(value) => updateSubtitleProfile("maxCps", value)}
                  />
                  <QualityNumberField
                    label="Min seconds"
                    value={subtitleProfile.minDuration}
                    min={SUBTITLE_PROFILE_LIMITS.minDuration[0]}
                    max={SUBTITLE_PROFILE_LIMITS.minDuration[1]}
                    step={0.1}
                    onChange={(value) => updateSubtitleProfile("minDuration", value)}
                  />
                  <QualityNumberField
                    label="Max seconds"
                    value={subtitleProfile.maxDuration}
                    min={SUBTITLE_PROFILE_LIMITS.maxDuration[0]}
                    max={SUBTITLE_PROFILE_LIMITS.maxDuration[1]}
                    step={0.5}
                    onChange={(value) => updateSubtitleProfile("maxDuration", value)}
                  />
                  <button className="secondary-button quality-wrap-button" type="button" onClick={wrapAllSubtitleCues}>
                    <WrapText size={16} aria-hidden />
                    Wrap cues
                  </button>
                </div>
              </div>
              <div className="lyrics-tools" data-testid="lyrics-tools">
                <label className="lyrics-field">
                  <span>Lyrics</span>
                  <textarea
                    data-testid="lyrics-input"
                    value={lyricsDraft}
                    onChange={(event) => updateLyricsDraft(event.target.value)}
                    placeholder="Paste lyrics"
                    rows={5}
                  />
                </label>
                <div className="lyrics-actions">
                  {lyricsStatus ? <span className="save-state">{lyricsStatus}</span> : null}
                  <button
                    className="ghost-button"
                    data-testid="lyrics-preview-button"
                    disabled={!lyricsDraft.trim() || isPreviewingLyrics}
                    onClick={previewLyrics}
                    type="button"
                  >
                    {isPreviewingLyrics ? <Loader2 className="spin" size={16} aria-hidden /> : <Search size={16} aria-hidden />}
                    Preview
                  </button>
                  <button
                    className="secondary-button"
                    data-testid="lyrics-align-button"
                    disabled={!lyricsPreview || isAligningLyrics}
                    onClick={alignLyrics}
                    type="button"
                  >
                    {isAligningLyrics ? <Loader2 className="spin" size={16} aria-hidden /> : <Captions size={16} aria-hidden />}
                    Align lyrics
                  </button>
                </div>
              </div>
              {lyricsPreview ? (
                <div className="lyrics-preview" data-testid="lyrics-preview">
                  {lyricsPreview.segments.map((segment) => (
                    <div className="lyrics-preview-row" key={segment.index}>
                      <time>{formatTime(segment.start)}</time>
                      <span>{segment.text}</span>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="transcript-layout">
                <div className="transcript-copy">
                  {draftSegments.map((segment, position) => (
                    <div
                      className={`transcript-row ${activeAudioSegmentIndex === segment.index ? "is-playing" : ""} ${
                        subtitleQuality.cues[position]?.issues.length ? "has-quality-warning" : ""
                      }`}
                      data-testid={`transcript-row-${segment.index}`}
                      key={segment.index}
                    >
                      <div className="segment-time-editor">
                        <strong>#{segment.index}</strong>
                        <label>
                          <span>Start</span>
                          <input
                            type="number"
                            min={0}
                            max={transcript.duration ?? undefined}
                            step={0.05}
                            value={segment.start}
                            aria-label={`Segment ${segment.index} start time in seconds`}
                            onFocus={beginSegmentEdit}
                            onBlur={finishSegmentEdit}
                            onChange={(event) => updateSegmentTiming(segment.index, "start", event.target.value)}
                          />
                        </label>
                        <label>
                          <span>End</span>
                          <input
                            type="number"
                            min={0}
                            max={transcript.duration ?? undefined}
                            step={0.05}
                            value={segment.end}
                            aria-label={`Segment ${segment.index} end time in seconds`}
                            onFocus={beginSegmentEdit}
                            onBlur={finishSegmentEdit}
                            onChange={(event) => updateSegmentTiming(segment.index, "end", event.target.value)}
                          />
                        </label>
                      </div>
                      <div className="segment-copy-editor">
                        <textarea
                          aria-label={`Transcript segment ${segment.index}`}
                          value={segment.text}
                          ref={(element) => {
                            if (element) segmentTextareasRef.current.set(segment.index, element);
                            else segmentTextareasRef.current.delete(segment.index);
                          }}
                          onFocus={beginSegmentEdit}
                          onBlur={finishSegmentEdit}
                          onSelect={(event) => segmentCaretsRef.current.set(segment.index, event.currentTarget.selectionStart)}
                          onChange={(event) => updateDraftSegment(segment.index, event.target.value)}
                          rows={2}
                        />
                        <div className="cue-diagnostics" aria-label={`Subtitle quality for segment ${segment.index}`}>
                          <span className="cue-stat">
                            {subtitleQuality.cues[position]?.duration.toFixed(1)}s / {formatReadingSpeed(subtitleQuality.cues[position]?.charactersPerSecond)} CPS
                          </span>
                          {subtitleQuality.cues[position]?.issues.map((issue) => (
                            <span className="cue-warning" key={issue.code}>
                              {issue.message}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="segment-actions">
                        <button
                          type="button"
                          title={activeJob?.media_url ? "Play from cue" : "Local preview media unavailable"}
                          aria-label={`Play segment ${segment.index}`}
                          disabled={!activeJob?.media_url}
                          onClick={() => playSubtitleCue(segment)}
                        >
                          <Play size={16} aria-hidden />
                        </button>
                        <button
                          type="button"
                          title="Split at cursor"
                          aria-label={`Split segment ${segment.index}`}
                          onClick={() => splitSegment(segment.index)}
                        >
                          <Scissors size={16} aria-hidden />
                        </button>
                        <button
                          type="button"
                          title="Merge with previous"
                          aria-label={`Merge segment ${segment.index} with previous`}
                          disabled={position === 0}
                          onClick={() => mergeSegmentWithPrevious(segment.index)}
                        >
                          <Combine size={16} aria-hidden />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <aside className="meta-strip">
                  <Metric label="Language" value={transcript.language ?? "auto"} />
                  <Metric label="Duration" value={transcript.duration ? formatTime(transcript.duration) : "unknown"} />
                  <Metric label="Segments" value={String(draftSegments.length)} />
                  <Metric label="Cue warnings" value={String(subtitleQuality.warningCueCount)} />
                </aside>
              </div>
            </>
          ) : (
            <div className="empty-transcript">Transcript will appear here when a job completes.</div>
          )}
        </section>
      </section>
    </main>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextField({
  label,
  value,
  placeholder,
  onChange
}: {
  label: string;
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function QualityNumberField({
  label,
  value,
  min,
  max,
  step,
  onChange
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="quality-number-field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => {
          if (event.target.value !== "") onChange(Number(event.target.value));
        }}
      />
    </label>
  );
}

function PanelHeading({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="panel-heading">
      {icon}
      <h3>{title}</h3>
    </div>
  );
}

function Progress({ status }: { status: JobStatus }) {
  const steps: JobStatus[] = ["queued", "extracting", "transcribing", "writing", "completed"];
  const activeIndex = status === "failed" || status === "cancelled" ? -1 : steps.indexOf(status);
  return (
    <div className={`progress-track ${status}`} aria-label={`Job status: ${status}`}>
      {steps.map((step, index) => (
        <span key={step} className={activeIndex >= 0 && index <= activeIndex ? "done" : ""}>
          {step}
        </span>
      ))}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function artifactIcon(key: string) {
  const props = { size: 16, "aria-hidden": true };
  if (key === "json") return <FileJson {...props} />;
  if (key === "audio") return <FileAudio {...props} />;
  if (key === "srt" || key === "vtt") return <Captions {...props} />;
  return <Download {...props} />;
}

function jobStatusIcon(status: JobStatus) {
  if (status === "completed") return <Check size={18} aria-hidden />;
  if (status === "failed" || status === "cancelled") return <XCircle size={18} aria-hidden />;
  if (status === "queued") return <Radio size={18} aria-hidden />;
  return <Loader2 className="spin" size={18} aria-hidden />;
}

function statusLabel(status: JobStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatDateTime(value: string | null) {
  if (!value) return "not started";
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}

function formatJobRuntime(job: Job) {
  const start = job.started_at ? new Date(job.started_at).getTime() : new Date(job.created_at).getTime();
  const end = job.completed_at ? new Date(job.completed_at).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "unknown";
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  return formatTime(seconds);
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function isZipArchive(file: File) {
  return file.name.toLowerCase().endsWith(".zip") && ZIP_MIME_TYPES.has(file.type);
}

function totalSelectedBytes(files: File[]) {
  return files.reduce((total, file) => total + file.size, 0);
}

function cloneSegments(segments: TranscriptSegment[]) {
  return segments.map((segment) => ({ ...segment }));
}

function segmentsEqual(left: TranscriptSegment[], right: TranscriptSegment[]) {
  return (
    left.length === right.length &&
    left.every((segment, index) => {
      const other = right[index];
      return (
        other !== undefined &&
        segment.index === other.index &&
        segment.start === other.start &&
        segment.end === other.end &&
        segment.text === other.text
      );
    })
  );
}

function segmentStructureEqual(left: TranscriptSegment[], right: TranscriptSegment[]) {
  return (
    left.length === right.length &&
    left.every((segment, index) => {
      const other = right[index];
      return other !== undefined && segment.start === other.start && segment.end === other.end;
    })
  );
}

function renumberSegments(segments: TranscriptSegment[]) {
  return segments.map((segment, index) => ({ ...segment, index: index + 1 }));
}

function validateSegmentTimings(segments: TranscriptSegment[], duration: number | null) {
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index];
    if (!Number.isFinite(segment.start) || !Number.isFinite(segment.end) || segment.start < 0) {
      return `Segment ${index + 1} has an invalid time`;
    }
    if (segment.end <= segment.start) return `Segment ${index + 1} must end after it starts`;
    if (index > 0 && segment.start < segments[index - 1].end) {
      return `Segment ${index + 1} overlaps segment ${index}`;
    }
    if (duration !== null && segment.end > duration + 0.001) {
      return `Segment ${index + 1} ends after the media duration`;
    }
  }
  return null;
}

function bestSplitPosition(text: string) {
  if (text.length < 2) return 0;
  const midpoint = Math.floor(text.length / 2);
  for (let distance = 0; distance < text.length; distance += 1) {
    const right = midpoint + distance;
    if (right > 0 && right < text.length && /\s/.test(text[right])) return right;
    const left = midpoint - distance;
    if (left > 0 && left < text.length && /\s/.test(text[left])) return left;
  }
  return midpoint;
}

function roundSeconds(seconds: number) {
  return Math.round(seconds * 1000) / 1000;
}

function escapeRegularExpression(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function loadSettings(): Settings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    if (parsed.version !== 1) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...parsed, version: 1 };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function loadSubtitleQualityProfile(): SubtitleQualityProfile {
  try {
    const raw = window.localStorage.getItem(SUBTITLE_QUALITY_KEY);
    if (!raw) return DEFAULT_SUBTITLE_QUALITY_PROFILE;
    const parsed = JSON.parse(raw) as Partial<SubtitleQualityProfile>;
    const profile = { ...DEFAULT_SUBTITLE_QUALITY_PROFILE };
    for (const field of Object.keys(profile) as (keyof SubtitleQualityProfile)[]) {
      const value = Number(parsed[field]);
      if (!Number.isFinite(value)) continue;
      const [minimum, maximum] = SUBTITLE_PROFILE_LIMITS[field];
      profile[field] = Math.min(maximum, Math.max(minimum, value));
    }
    if (profile.minDuration > profile.maxDuration) profile.maxDuration = profile.minDuration;
    return profile;
  } catch {
    return DEFAULT_SUBTITLE_QUALITY_PROFILE;
  }
}

function formatReadingSpeed(value: number | undefined) {
  if (value === undefined) return "0.0";
  return Number.isFinite(value) ? value.toFixed(1) : "n/a";
}

function formatPreciseTime(seconds: number) {
  const totalTenths = Math.max(0, Math.floor(seconds * 10));
  const hours = Math.floor(totalTenths / 36_000);
  const minutes = Math.floor((totalTenths % 36_000) / 600);
  const rest = Math.floor((totalTenths % 600) / 10);
  const tenths = totalTenths % 10;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}.${tenths}`;
  }
  return `${minutes}:${String(rest).padStart(2, "0")}.${tenths}`;
}

function formatTime(seconds: number) {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const rest = safeSeconds % 60;
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

export default App;
