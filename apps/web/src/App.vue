<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import {
  AnalysisApiClient,
  type AnalysisJob,
  createIdempotencyKey,
  isTerminalStatus,
  type UploadProgress,
} from "./api/analysis";
import { AuthApiClient, type AuthUser } from "./api/auth";
import AdminAccountsPanel from "./components/AdminAccountsPanel.vue";
import AuthPanel from "./components/AuthPanel.vue";
import AudioWaveform from "./components/AudioWaveform.vue";
import AnalysisDashboard from "./components/AnalysisDashboard.vue";
import AiMasteringChanges from "./components/AiMasteringChanges.vue";
import BeforeAfterPlayer from "./components/BeforeAfterPlayer.vue";
import GuidePage from "./components/GuidePage.vue";
import InfoTip from "./components/InfoTip.vue";
import InteractivePreview from "./components/InteractivePreview.vue";
import TechnicalReferencePage from "./components/TechnicalReferencePage.vue";
import { backendSettings, type InteractiveSettings } from "./masteringParameters";
import {
  masteringIntents,
  type MasteringIntent,
} from "./masteringPresets";
import type { Locale } from "./i18n";
import { translate, translateApiError, translateFinding } from "./i18n";
import {
  recommendationFindings,
  shouldScrollToComparison,
  stageIndex,
} from "./presentation";

type TransferPhase = "idle" | "uploading" | "server_accepting" | "failed";

const intents: readonly MasteringIntent[] = masteringIntents;
const storedLocale = localStorage.getItem("openmaster-locale");
const locale = ref<Locale>(
  storedLocale === "fr" || (storedLocale === null && navigator.language.startsWith("fr"))
    ? "fr"
    : "en",
);
const t = (key: string, variables?: Record<string, string | number>) =>
  translate(locale.value, key, variables);
const intentName = (intent: MasteringIntent) => t(`intent${intent.copy}`);
const intentNote = (intent: MasteringIntent) => t(`intent${intent.copy}Note`);
const intentDescription = (intent: MasteringIntent) =>
  t(`intent${intent.copy}Description`);
const pipelineStages = computed(() => [
  { key: "source", label: t("sourceReceived") },
  { key: "analysis", label: t("analysis") },
  { key: "settings", label: locale.value === "fr" ? "Pré-réglages" : "Pre-settings" },
  { key: "mastering", label: t("mastering") },
  { key: "ready", label: t("ready") },
]);
const page = ref<"studio" | "guide" | "technical" | "admin">("studio");
const pointerX = ref(50);
const pointerY = ref(12);
const ambientStyle = computed(() => ({
  "--pointer-x": `${pointerX.value}%`,
  "--pointer-y": `${pointerY.value}%`,
}));
let pointerFrame = 0;
let pendingPointer: PointerEvent | null = null;

function updateAmbientPointer(event: PointerEvent): void {
  pendingPointer = event;
  if (pointerFrame) return;
  pointerFrame = requestAnimationFrame(() => {
    if (pendingPointer) {
      pointerX.value = pendingPointer.clientX / window.innerWidth * 100;
      pointerY.value = pendingPointer.clientY / window.innerHeight * 100;
    }
    pendingPointer = null;
    pointerFrame = 0;
  });
}
const activeIntent = ref("Streaming");
const activeIntentLabel = computed(() => {
  if (activeIntent.value === "Custom") return t("custom");
  const intent = intents.find((candidate) => candidate.key === activeIntent.value);
  return intent ? intentName(intent) : t("custom");
});
const activeIntentDescription = computed(() => {
  const intent = intents.find((candidate) => candidate.key === activeIntent.value);
  return intent ? intentDescription(intent) : t("intentTip");
});
const extraHeadroom = ref(false);
const gentleCorrection = ref(false);
const highResolution = ref(true);
const selectedFile = ref<File | null>(null);
const sourceUrl = ref<string | null>(null);
const job = ref<AnalysisJob | null>(null);
const recentProjects = ref<AnalysisJob[]>([]);
const historyOpen = ref(false);
const projectRootId = ref<string | null>(null);
const renameValue = ref("");
const renameSaved = ref(false);
const error = ref<string | null>(null);
const submitting = ref(false);
const transferPhase = ref<TransferPhase>("idle");
const uploadPercent = ref(0);
const uploadLoadedBytes = ref(0);
const uploadTotalBytes = ref(0);
const beforeAfterAnchor = ref<HTMLElement | null>(null);
const targetLufs = ref(-14);
const bitDepth = ref(24);
const maximumGainAdjustmentDb = ref(12);
const ceilingDbfs = ref(-1);
const eqLowGainDb = ref(0);
const eqMidGainDb = ref(0);
const eqHighGainDb = ref(0);
const clipperDriveDb = ref(1);
const limiterLookaheadMs = ref(3);
const limiterReleaseMs = ref(80);
const highPassEnabled = ref(true);
const highPassCutoffHz = ref(25);
const dynamicEqReductionDb = ref(0);
const bassControlReductionDb = ref(0);
const deEsserReductionDb = ref(0);
const saturationAmount = ref(0);
const aiAssistEnabled = ref(false);
const showTechnical = ref(false);
const client = new AnalysisApiClient();
const authClient = new AuthApiClient();
const authReady = ref(false);
const currentUser = ref<AuthUser | null>(null);
const defaultIntent = intents.find((intent) => intent.key === "Streaming");
if (defaultIntent) applyIntent(defaultIntent);
const canSubmit = computed(() => selectedFile.value !== null && !submitting.value);
const currentSettings = computed<InteractiveSettings>(() => ({
  targetLufs: targetLufs.value,
  maximumGainAdjustmentDb: maximumGainAdjustmentDb.value,
  ceilingDbfs: ceilingDbfs.value,
  eqLowGainDb: eqLowGainDb.value,
  eqMidGainDb: eqMidGainDb.value,
  eqHighGainDb: eqHighGainDb.value,
  clipperDriveDb: clipperDriveDb.value,
  limiterLookaheadMs: limiterLookaheadMs.value,
  limiterReleaseMs: limiterReleaseMs.value,
  highPassEnabled: highPassEnabled.value,
  highPassCutoffHz: highPassCutoffHz.value,
  dynamicEqReductionDb: dynamicEqReductionDb.value,
  bassControlReductionDb: bassControlReductionDb.value,
  deEsserReductionDb: deEsserReductionDb.value,
  saturationAmount: saturationAmount.value,
  bitDepth: bitDepth.value,
  bit_depth: bitDepth.value,
  ai_assist_enabled: aiAssistEnabled.value,
}));
const currentStage = computed(() => {
  if (!job.value) return -1;
  if (job.value.status === "failed") return job.value.result ? 3 : 1;
  return stageIndex(job.value.status);
});
const progressPercent = computed(() => {
  if (!job.value) return 0;
  return {
    queued: 20,
    running: 40,
    analyzed: 60,
    mastering: 80,
    retry_wait: 40,
    succeeded: 100,
    failed: Math.max(0, currentStage.value * 20),
  }[job.value.status];
});
const aiAssistance = computed<Record<string, unknown> | null>(() => {
  const value = job.value?.mastering_result?.ai_assistance;
  return typeof value === "object" && value !== null
    ? value as Record<string, unknown>
    : null;
});
const analyzedSourceLufs = computed(() => {
  const value = job.value?.result?.lufs;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
});
const findings = computed(() =>
  recommendationFindings(job.value?.recommendation).map((finding) => ({
    ...finding,
    message: translateFinding(locale.value, finding.code, finding.message),
  })),
);
const fileSize = computed(() =>
  selectedFile.value ? `${(selectedFile.value.size / 1024 / 1024).toFixed(1)} MB` : "",
);
const uploadByteProgress = computed(() => {
  if (uploadTotalBytes.value <= 0) return "";
  return `${formatBytes(uploadLoadedBytes.value)} / ${formatBytes(uploadTotalBytes.value)}`;
});
let pollTimer: ReturnType<typeof setTimeout> | undefined;
let uploadController: AbortController | undefined;
let uploadIdempotencyKey: string | undefined;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDb(value: number): string {
  return value.toFixed(2).replace(/0$/, "");
}

function stopPolling(): void {
  if (pollTimer) clearTimeout(pollTimer);
  pollTimer = undefined;
}

function applyIntent(intent: MasteringIntent): void {
  activeIntent.value = intent.key;
  targetLufs.value = intent.target;
  ceilingDbfs.value = intent.ceiling;
  maximumGainAdjustmentDb.value = intent.gain;
  bitDepth.value = intent.depth;
  [eqLowGainDb.value, eqMidGainDb.value, eqHighGainDb.value] = intent.eq;
  [
    dynamicEqReductionDb.value,
    bassControlReductionDb.value,
    deEsserReductionDb.value,
    saturationAmount.value,
  ] = intent.spectral;
  clipperDriveDb.value = intent.clip;
  limiterLookaheadMs.value = intent.limiterLookaheadMs;
  limiterReleaseMs.value = intent.limiterReleaseMs;
  highPassEnabled.value = intent.highPassEnabled;
  highPassCutoffHz.value = intent.highPassCutoffHz;
  aiAssistEnabled.value = intent.aiAssistEnabled;
  extraHeadroom.value = intent.ceiling <= -1.5;
  gentleCorrection.value = intent.gain <= 6;
  highResolution.value = intent.depth >= 24;
}

function toggleHeadroom(): void {
  extraHeadroom.value = !extraHeadroom.value;
  ceilingDbfs.value = extraHeadroom.value ? -2 : -1;
  activeIntent.value = "Custom";
}

function toggleCorrection(): void {
  gentleCorrection.value = !gentleCorrection.value;
  maximumGainAdjustmentDb.value = gentleCorrection.value ? 6 : 12;
  activeIntent.value = "Custom";
}

function toggleResolution(): void {
  highResolution.value = !highResolution.value;
  bitDepth.value = highResolution.value ? 24 : 16;
  activeIntent.value = "Custom";
}

function selectFile(event: Event): void {
  const target = event.target as HTMLInputElement;
  setFile(target.files?.[0] ?? null);
}

function dropFile(event: DragEvent): void {
  if (submitting.value) return;
  setFile(event.dataTransfer?.files[0] ?? null);
}

function setFile(file: File | null): void {
  if (submitting.value) return;
  stopPolling();
  if (sourceUrl.value?.startsWith("blob:")) URL.revokeObjectURL(sourceUrl.value);
  selectedFile.value = file;
  sourceUrl.value = file ? URL.createObjectURL(file) : null;
  uploadIdempotencyKey = file ? createIdempotencyKey() : undefined;
  job.value = null;
  projectRootId.value = null;
  error.value = null;
  transferPhase.value = "idle";
  uploadPercent.value = 0;
  uploadLoadedBytes.value = 0;
  uploadTotalBytes.value = 0;
}

async function loadHistory(): Promise<void> {
  try {
    recentProjects.value = await client.listRecent();
  } catch {
    recentProjects.value = [];
  }
}

function openProject(project: AnalysisJob): void {
  stopPolling();
  if (sourceUrl.value?.startsWith("blob:")) URL.revokeObjectURL(sourceUrl.value);
  job.value = project;
  projectRootId.value = project.parent_job_id ?? project.id;
  renameValue.value = project.project_name ?? project.original_filename.replace(/\.[^.]+$/, "");
  historyOpen.value = false;
  selectedFile.value = null;
  sourceUrl.value = project.source_preview_url ?? null;
  uploadIdempotencyKey = undefined;
  transferPhase.value = "idle";
  uploadPercent.value = 0;
  uploadLoadedBytes.value = 0;
  uploadTotalBytes.value = 0;
  error.value = null;
  const settings = project.interactive_settings;
  if (settings) {
    targetLufs.value = Number(settings.target_lufs ?? targetLufs.value);
    maximumGainAdjustmentDb.value = Number(settings.maximum_gain_adjustment_db ?? maximumGainAdjustmentDb.value);
    ceilingDbfs.value = Number(settings.ceiling_dbfs ?? ceilingDbfs.value);
    eqLowGainDb.value = Number(settings.eq_low_gain_db ?? eqLowGainDb.value);
    eqMidGainDb.value = Number(settings.eq_mid_gain_db ?? eqMidGainDb.value);
    eqHighGainDb.value = Number(settings.eq_high_gain_db ?? eqHighGainDb.value);
    clipperDriveDb.value = Number(settings.clipper_drive_db ?? clipperDriveDb.value);
    limiterLookaheadMs.value = Number(settings.limiter_lookahead_ms ?? limiterLookaheadMs.value);
    limiterReleaseMs.value = Number(settings.limiter_release_ms ?? limiterReleaseMs.value);
    highPassEnabled.value = Boolean(settings.high_pass_enabled ?? highPassEnabled.value);
    highPassCutoffHz.value = Number(settings.high_pass_cutoff_hz ?? highPassCutoffHz.value);
    dynamicEqReductionDb.value = Number(settings.dynamic_eq_reduction_db ?? dynamicEqReductionDb.value);
    bassControlReductionDb.value = Number(settings.bass_control_reduction_db ?? bassControlReductionDb.value);
    deEsserReductionDb.value = Number(settings.de_esser_reduction_db ?? deEsserReductionDb.value);
    saturationAmount.value = Number(settings.saturation_amount ?? saturationAmount.value);
    bitDepth.value = Number(settings.bit_depth ?? bitDepth.value);
    aiAssistEnabled.value = Boolean(settings.ai_assist_enabled ?? aiAssistEnabled.value);
  }
  activeIntent.value = "Custom";
  if (!isTerminalStatus(project.status)) schedulePoll();
}

async function renameProject(): Promise<void> {
  if (!job.value || !renameValue.value.trim()) return;
  try {
    const renamed = await client.rename(projectRootId.value ?? job.value.id, renameValue.value);
    job.value = { ...job.value, project_name: renamed.project_name };
    await loadHistory();
    renameSaved.value = true;
    window.setTimeout(() => { renameSaved.value = false; }, 1_400);
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : t("requestFailed");
  }
}

function requestMaster(): void {
  if (!canSubmit.value) return;
  void submit();
}

function requestFinalRender(): void {
  if (!job.value || submitting.value) return;
  void renderFinal();
}

async function saveSettings(): Promise<void> {
  if (!job.value) return;
  try {
    job.value = await client.saveSettings(job.value.id, {
      ...backendSettings(currentSettings.value),
      bit_depth: bitDepth.value,
      ai_assist_enabled: aiAssistEnabled.value,
      high_pass_enabled: highPassEnabled.value,
    });
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : t("requestFailed");
  }
}

async function startMasterDecision(): Promise<void> {
  if (!job.value || job.value.status !== "analyzed" || submitting.value) return;
  submitting.value = true;
  error.value = null;
  try {
    job.value = await client.startMaster(job.value.id, {
      ...backendSettings(currentSettings.value),
      bit_depth: bitDepth.value,
      ai_assist_enabled: aiAssistEnabled.value,
      high_pass_enabled: highPassEnabled.value,
    });
    await loadHistory();
    schedulePoll();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : t("requestFailed");
  } finally {
    submitting.value = false;
  }
}

async function renderFinal(): Promise<void> {
  if (!job.value) return;
  submitting.value = true;
  try {
    await saveSettings();
    if (!job.value) return;
    job.value = await client.renderFinal(projectRootId.value ?? job.value.id, {
      ...backendSettings(currentSettings.value),
      bit_depth: bitDepth.value,
      ai_assist_enabled: aiAssistEnabled.value,
      high_pass_enabled: highPassEnabled.value,
    }, createIdempotencyKey());
    schedulePoll();
  } catch (reason) {
    error.value = reason instanceof Error ? translateApiError(locale.value, reason.message) : t("requestFailed");
  } finally {
    submitting.value = false;
  }
}

function resetInteractiveSettings(): void {
  eqLowGainDb.value = 0; eqMidGainDb.value = 0; eqHighGainDb.value = 0;
  highPassCutoffHz.value = 25; highPassEnabled.value = true;
  dynamicEqReductionDb.value = 0; bassControlReductionDb.value = 0;
  deEsserReductionDb.value = 0; ceilingDbfs.value = -1;
  targetLufs.value = -14; maximumGainAdjustmentDb.value = 12;
  clipperDriveDb.value = 0; limiterLookaheadMs.value = 3;
  limiterReleaseMs.value = 80; saturationAmount.value = 0; bitDepth.value = 24;
  aiAssistEnabled.value = false;
  extraHeadroom.value = false;
  gentleCorrection.value = false;
  highResolution.value = true;
  activeIntent.value = "";
  document.querySelector(".preset-grid")?.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function submit(): Promise<void> {
  if (!selectedFile.value) return;
  const sourceFile = selectedFile.value;
  const controller = new AbortController();
  uploadController = controller;
  submitting.value = true;
  error.value = null;
  job.value = null;
  transferPhase.value = "uploading";
  uploadPercent.value = 0;
  uploadLoadedBytes.value = 0;
  uploadTotalBytes.value = sourceFile.size;
  const idempotencyKey = uploadIdempotencyKey ?? createIdempotencyKey();
  uploadIdempotencyKey = idempotencyKey;
  try {
    job.value = await client.submit(
      sourceFile,
      idempotencyKey,
      targetLufs.value,
      bitDepth.value,
      maximumGainAdjustmentDb.value,
      ceilingDbfs.value,
      eqLowGainDb.value,
      eqMidGainDb.value,
      eqHighGainDb.value,
      clipperDriveDb.value,
      limiterLookaheadMs.value,
      limiterReleaseMs.value,
      highPassEnabled.value,
      highPassCutoffHz.value,
      dynamicEqReductionDb.value,
      bassControlReductionDb.value,
      deEsserReductionDb.value,
      saturationAmount.value,
      aiAssistEnabled.value,
      (progress: UploadProgress) => {
        uploadPercent.value = progress.percent;
        uploadLoadedBytes.value = progress.loadedBytes;
        uploadTotalBytes.value = progress.totalBytes;
        transferPhase.value = progress.percent >= 100 ? "server_accepting" : "uploading";
      },
      controller.signal,
    );
    transferPhase.value = "idle";
    projectRootId.value = job.value.id;
    renameValue.value = sourceFile.name.replace(/\.[^.]+$/, "");
    await loadHistory();
    schedulePoll();
  } catch (reason) {
    if (!(reason instanceof DOMException && reason.name === "AbortError")) {
      transferPhase.value = "failed";
      error.value =
        reason instanceof Error
          ? translateApiError(locale.value, reason.message)
          : t("requestFailed");
    }
  } finally {
    if (uploadController === controller) uploadController = undefined;
    submitting.value = false;
  }
}

function schedulePoll(delayMs = 1_000): void {
  stopPolling();
  if (!job.value || isTerminalStatus(job.value.status)) return;
  const jobId = job.value.id;
  let nextDelayMs = 1_000;
  pollTimer = setTimeout(async () => {
    pollTimer = undefined;
    try {
      const updated = await client.get(jobId);
      if (job.value?.id !== jobId) return;
      job.value = updated;
      error.value = null;
      if (isTerminalStatus(updated.status)) await loadHistory();
    } catch (reason) {
      if (job.value?.id === jobId) {
        nextDelayMs = 2_500;
        error.value =
          reason instanceof Error
            ? translateApiError(locale.value, reason.message)
            : t("statusFailed");
      }
    }
    if (job.value?.id === jobId) schedulePoll(nextDelayMs);
  }, delayMs);
}

onBeforeUnmount(() => {
  cancelAnimationFrame(pointerFrame);
  uploadController?.abort();
  stopPolling();
  if (sourceUrl.value?.startsWith("blob:")) URL.revokeObjectURL(sourceUrl.value);
});
async function bootstrapAccount(): Promise<void> {
  try {
    currentUser.value = await authClient.me();
    if (currentUser.value) await loadHistory();
  } catch {
    currentUser.value = null;
  } finally {
    authReady.value = true;
  }
}

async function accountAuthenticated(user: AuthUser): Promise<void> {
  currentUser.value = user;
  page.value = "studio";
  await loadHistory();
}

async function logout(): Promise<void> {
  try {
    await authClient.logout();
  } finally {
    stopPolling();
    currentUser.value = null;
    job.value = null;
    recentProjects.value = [];
    historyOpen.value = false;
    selectedFile.value = null;
    sourceUrl.value = null;
  }
}

onMounted(bootstrapAccount);
watch(
  locale,
  (value) => {
    localStorage.setItem("openmaster-locale", value);
    document.documentElement.lang = value;
  },
  { immediate: true },
);
watch(
  () => job.value
    ? { id: job.value.id, status: job.value.status }
    : null,
  async (current, previous) => {
    if (!shouldScrollToComparison(previous, current)) return;
    await nextTick();
    beforeAfterAnchor.value?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "start",
    });
  },
  { flush: "post" },
);
</script>

<template>
  <div class="app-shell" :style="ambientStyle" @pointermove.passive="updateAmbientPointer">
    <div class="ambient-field" aria-hidden="true">
      <i class="ambient-orb orb-one"></i>
      <i class="ambient-orb orb-two"></i>
      <i class="ambient-orb orb-three"></i>
      <svg class="ambient-wave" viewBox="0 0 1440 260" preserveAspectRatio="none">
        <path d="M0 140 C120 20 220 240 350 120 S590 55 720 145 S960 245 1090 110 S1320 25 1440 150" />
        <path d="M0 170 C130 80 250 220 390 155 S620 80 760 165 S1010 220 1150 140 S1340 90 1440 175" />
      </svg>
      <div class="ambient-grid"></div>
    </div>
    <nav class="topbar">
      <button class="brand brand-button" type="button" :aria-label="`OpenMaster ${t('studio')}`" @click="page = 'studio'">
        <span class="brand-mark"><i></i><i></i><i></i><i></i></span>
        <span>OPEN<span>MASTER</span></span>
      </button>
      <span class="studio-status"><i></i> {{ t("engineOnline") }}</span>
      <div class="nav-links">
        <button type="button" :class="{ active: page === 'studio' }" @click="page = 'studio'">{{ t("studio") }}</button>
        <button type="button" :class="{ active: page === 'guide' }" @click="page = 'guide'">{{ t("guide") }}</button>
        <button type="button" :class="{ active: page === 'technical' }" @click="page = 'technical'">{{ t("technical") }}</button>
        <button
          v-if="currentUser?.role === 'admin'"
          type="button"
          :class="{ active: page === 'admin' }"
          @click="page = 'admin'"
        >Admin</button>
        <label class="language-selector">
          <span class="sr-only">Language</span>
          <select v-model="locale" aria-label="Language / Langue">
            <option value="en">EN</option>
            <option value="fr">FR</option>
          </select>
        </label>
        <button
          v-if="currentUser"
          class="account-chip"
          type="button"
          :title="currentUser.email"
          @click="logout"
        >
          <span>{{ currentUser.display_name.slice(0, 1).toUpperCase() }}</span>
          <b>{{ currentUser.display_name }}</b>
          <small>{{ locale === "fr" ? "Déconnexion" : "Sign out" }}</small>
        </button>
        <a
          class="github-link"
          href="https://github.com/lucaslamy/OpenMaster"
          target="_blank"
          rel="noopener noreferrer"
        >{{ t("sourceLink") }}</a>
      </div>
    </nav>

    <GuidePage
      v-if="page === 'guide'"
      :locale="locale"
      @back="page = 'studio'"
      @technical="page = 'technical'"
    />
    <TechnicalReferencePage
      v-else-if="page === 'technical'"
      :locale="locale"
      @back="page = 'guide'"
      @studio="page = 'studio'"
    />
    <AdminAccountsPanel
      v-else-if="page === 'admin' && currentUser?.role === 'admin'"
      :locale="locale"
      @back="page = 'studio'"
    />
    <main v-else-if="!authReady" class="auth-loading" aria-live="polite">
      <i></i><span>{{ locale === "fr" ? "Ouverture de la session…" : "Opening session…" }}</span>
    </main>
    <AuthPanel
      v-else-if="!currentUser"
      :locale="locale"
      @authenticated="accountAuthenticated"
    />
    <main v-else>
      <header class="hero">
        <div class="signal-sprites" aria-hidden="true">
          <i></i><i></i><i></i><i></i><i></i>
        </div>
        <p class="eyebrow">{{ t("workspace") }}</p>
        <h1>{{ t("heroTitle") }}<br /><em>{{ t("heroEmphasis") }}</em></h1>
        <p class="hero-copy">{{ t("heroCopy") }}</p>
        <div class="hero-spectrum" aria-hidden="true">
          <i v-for="height in [24, 48, 31, 73, 91, 58, 42, 76, 64, 37, 53, 82, 45, 68, 29, 57]" :key="height" :style="{ height: `${height}%` }"></i>
        </div>
      </header>

      <button
        v-if="recentProjects.length"
        class="history-trigger"
        type="button"
        :aria-expanded="historyOpen"
        aria-controls="project-history-drawer"
        @click="historyOpen = true"
      >
        <span>⌁</span><b>{{ locale === "fr" ? "Projets" : "Projects" }}</b>
      </button>
      <div v-if="historyOpen" class="history-backdrop" @click.self="historyOpen = false" @keydown.esc="historyOpen = false">
      <section id="project-history-drawer" class="project-history panel" role="dialog" aria-modal="true" aria-labelledby="project-history-title">
        <div class="panel-heading">
          <div><span class="step">↺</span><h2 id="project-history-title">{{ locale === "fr" ? "20 derniers projets" : "Latest 20 projects" }}</h2></div>
          <button class="drawer-close" type="button" :aria-label="locale === 'fr' ? 'Fermer les projets' : 'Close projects'" @click="historyOpen = false">×</button>
        </div>
        <div class="history-list">
          <button
            v-for="project in recentProjects"
            :key="project.id"
            type="button"
            :class="{ active: job?.id === project.id }"
            @click="openProject(project)"
          >
            <strong>{{ project.project_name || project.original_filename }}</strong>
            <small>{{ project.status }} · {{ project.created_at ? new Date(project.created_at).toLocaleString(locale) : project.id.slice(0, 8) }}</small>
          </button>
        </div>
      </section>
      </div>

      <InteractivePreview
        v-if="job?.result && sourceUrl"
        class="sticky-preview"
        :url="sourceUrl"
        :settings="currentSettings"
        :locale="locale"
        :source-lufs="analyzedSourceLufs"
        @reset="resetInteractiveSettings"
      />

      <form class="studio-grid" @submit.prevent="requestMaster">
        <section v-if="!job?.result" class="panel source-panel">
          <div class="panel-heading">
            <div><span class="step">01</span><h2>{{ t("source") }}</h2></div>
            <span v-if="selectedFile" class="format-pill">{{ selectedFile.name.split(".").pop()?.toUpperCase() }}</span>
          </div>

          <label
            class="dropzone"
            :class="{ transferring: submitting }"
            for="audio-file"
            :aria-disabled="submitting"
            @dragover.prevent
            @drop.prevent="dropFile"
          >
            <input
              id="audio-file"
              type="file"
              accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.opus,.aiff"
              :disabled="submitting"
              @change="selectFile"
            />
            <template v-if="selectedFile">
              <span class="file-icon">♫</span>
              <strong>{{ selectedFile.name }}</strong>
              <small>{{ fileSize }} · {{ t("ready") }}</small>
              <span class="replace">{{ t("chooseAnother") }}</span>
            </template>
            <template v-else>
              <span class="upload-icon">↑</span>
              <strong>{{ t("dropMix") }}</strong>
              <small>WAV, FLAC, MP3, AIFF, M4A, OGG or Opus</small>
              <span class="replace">{{ t("browse") }}</span>
            </template>
          </label>
          <AudioWaveform :file="selectedFile" :locale="locale" />
          <div
            v-if="transferPhase !== 'idle'"
            class="upload-progress-card"
            :class="{ failed: transferPhase === 'failed' }"
          >
            <div class="upload-progress-heading">
              <span class="upload-loader" aria-hidden="true">
                <i></i><i></i><i></i>
              </span>
              <div>
                <strong aria-live="polite">
                  {{
                    transferPhase === "server_accepting"
                      ? t("sourceSent")
                      : transferPhase === "failed"
                        ? t("uploadInterrupted")
                        : t("uploadingSource")
                  }}
                </strong>
                <small>
                  {{
                    transferPhase === "server_accepting"
                      ? t("validatingSource")
                      : transferPhase === "failed"
                        ? t("uploadRetry")
                        : uploadByteProgress
                  }}
                </small>
              </div>
              <output v-if="transferPhase !== 'failed'">{{ uploadPercent }}%</output>
            </div>
            <div
              v-if="transferPhase !== 'failed'"
              class="upload-progress-track"
              :class="{ accepting: transferPhase === 'server_accepting' }"
              role="progressbar"
              :aria-valuenow="uploadPercent"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="t('uploadingSource')"
            >
              <i :style="{ width: `${uploadPercent}%` }"></i>
            </div>
          </div>
          <button v-if="selectedFile && !job" class="master-button" type="submit" :disabled="!canSubmit">
            <span>{{ submitting ? t("uploadSource") : (locale === "fr" ? "Téléverser puis analyser" : "Upload and analyze") }}</span>
            <b>→</b>
          </button>
        </section>

        <aside
          v-if="job?.result && !['queued', 'running', 'mastering', 'retry_wait'].includes(job.status)"
          class="panel settings-panel"
        >
          <div class="panel-heading">
            <div><span class="step">02</span><h2>{{ t("direction") }}</h2></div>
          </div>

          <div class="project-rename">
            <label for="project-name">{{ locale === "fr" ? "Nom du projet" : "Project name" }}</label>
            <div :class="{ saved: renameSaved }">
              <input id="project-name" v-model="renameValue" maxlength="120" />
              <button type="button" @click="renameProject">{{ renameSaved ? "✓" : "↵" }}</button>
            </div>
            <small v-if="renameSaved" class="rename-confirmation">{{ locale === "fr" ? "Nom enregistré" : "Name saved" }}</small>
          </div>

          <fieldset>
            <legend class="control-heading grouped-control-heading">
              <span>{{ t("masteringIntent") }} <InfoTip :text="t('intentTip')" /></span>
            </legend>
            <div class="preset-grid">
              <button
                v-for="intent in intents"
                :key="intent.key"
                class="preset"
                :class="{ active: activeIntent === intent.key, featured: intent.featured }"
                :title="intentDescription(intent)"
                type="button"
                @click="applyIntent(intent)"
              >
                <span><strong>{{ intentName(intent) }}</strong><small>{{ intentNote(intent) }}</small></span>
                <b>{{ intent.target }}<small> LUFS</small></b>
              </button>
            </div>
            <p class="preset-description">{{ activeIntentDescription }}</p>
          </fieldset>

          <div class="settings-columns">
          <div class="settings-column">
          <fieldset class="continuous-control">
            <legend class="control-heading">
              <span>{{ t("customTarget") }} <InfoTip :text="t('customTargetTip')" /></span>
              <output>{{ targetLufs.toFixed(1) }} LUFS</output>
            </legend>
            <input
              v-model.number="targetLufs"
              type="range"
              min="-24"
              max="-8"
              step="0.5"
              :aria-label="t('customTarget')"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>{{ t("dynamic") }} −24</span><span>{{ t("loud") }} −8</span></div>
          </fieldset>

          <fieldset>
            <legend class="control-heading">
              <span>{{ t("wavDepth") }} <InfoTip :text="t('wavDepthTip')" /></span>
            </legend>
            <div class="segments">
              <button
                v-for="depth in [16, 24, 32]"
                :key="depth"
                type="button"
                :class="{ active: bitDepth === depth }"
                @click="bitDepth = depth; activeIntent = 'Custom'"
              >{{ depth }} bit</button>
            </div>
          </fieldset>

          <fieldset class="continuous-control">
            <legend class="control-heading">
              <span>{{ t("limiterCeiling") }} <InfoTip :text="t('limiterTip')" /></span>
              <output>{{ ceilingDbfs.toFixed(1) }} dBFS</output>
            </legend>
            <input
              v-model.number="ceilingDbfs"
              type="range"
              min="-3"
              max="-0.1"
              step="0.1"
              :aria-label="t('limiterCeiling')"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>{{ t("safer") }} −3 dB</span><span>{{ t("hot") }} −0.1 dB</span></div>
          </fieldset>

          <fieldset class="continuous-control">
            <legend class="control-heading">
              <span>{{ t("maxCorrection") }} <InfoTip :text="t('correctionTip')" /></span>
              <output>±{{ maximumGainAdjustmentDb.toFixed(0) }} dB</output>
            </legend>
            <input
              v-model.number="maximumGainAdjustmentDb"
              type="range"
              min="0"
              max="12"
              step="1"
              :aria-label="t('maxCorrection')"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>{{ t("conservative") }}</span><span>{{ t("maximum") }}</span></div>
          </fieldset>

          <fieldset class="advanced-dsp">
            <legend class="control-heading grouped-control-heading">
              <span>{{ t("tonalEqualizer") }} <InfoTip :text="t('tonalEqualizerTip')" /></span>
            </legend>
            <div class="eq-curve" aria-hidden="true">
              <svg viewBox="0 0 300 70" preserveAspectRatio="none">
                <path class="eq-zero" d="M0 35 H300" />
                <polyline
                  :points="`0,${35 - eqLowGainDb * 4} 75,${35 - eqLowGainDb * 4} 150,${35 - eqMidGainDb * 4} 225,${35 - eqHighGainDb * 4} 300,${35 - eqHighGainDb * 4}`"
                />
              </svg>
            </div>
            <div class="mini-control">
              <label for="eq-low">{{ t("eqLow") }} <small>100 Hz</small></label>
              <output>{{ formatDb(eqLowGainDb) }} dB</output>
              <input id="eq-low" v-model.number="eqLowGainDb" type="range" min="-6" max="6" step="0.25" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="eq-mid">{{ t("eqMid") }} <small>1 kHz</small></label>
              <output>{{ formatDb(eqMidGainDb) }} dB</output>
              <input id="eq-mid" v-model.number="eqMidGainDb" type="range" min="-6" max="6" step="0.25" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="eq-high">{{ t("eqHigh") }} <small>10 kHz</small></label>
              <output>{{ formatDb(eqHighGainDb) }} dB</output>
              <input id="eq-high" v-model.number="eqHighGainDb" type="range" min="-6" max="6" step="0.25" @input="activeIntent = 'Custom'" />
            </div>
          </fieldset>

          </div>
          <div class="settings-column">
          <fieldset class="advanced-dsp spectral-dynamics-fieldset" aria-labelledby="spectral-dynamics-heading">
            <legend id="spectral-dynamics-heading" class="control-heading grouped-control-heading">
              <span>{{ t("spectralDynamics") }} <InfoTip :text="t('spectralDynamicsTip')" /></span>
            </legend>
            <div class="mini-control switch-control">
              <label for="high-pass-enabled">{{ t("highPass") }} <InfoTip :text="t('highPassTip')" /></label>
              <input id="high-pass-enabled" v-model="highPassEnabled" type="checkbox" @change="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="high-pass-cutoff">{{ t("highPassCutoff") }}</label>
              <output>{{ highPassCutoffHz.toFixed(0) }} Hz</output>
              <input id="high-pass-cutoff" v-model.number="highPassCutoffHz" type="range" min="15" max="80" step="1" :disabled="!highPassEnabled" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="dynamic-eq">{{ t("dynamicEq") }} <small>· {{ locale === "fr" ? "rendu final" : "final render" }}</small> <InfoTip :text="t('dynamicEqTip')" /></label>
              <output>{{ dynamicEqReductionDb.toFixed(1) }} dB</output>
              <input id="dynamic-eq" v-model.number="dynamicEqReductionDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="bass-control">{{ t("bassControl") }} <small>· {{ locale === "fr" ? "rendu final" : "final render" }}</small> <InfoTip :text="t('bassControlTip')" /></label>
              <output>{{ bassControlReductionDb.toFixed(1) }} dB</output>
              <input id="bass-control" v-model.number="bassControlReductionDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="de-esser">{{ t("deEsser") }} <small>· {{ locale === "fr" ? "rendu final" : "final render" }}</small> <InfoTip :text="t('deEsserTip')" /></label>
              <output>{{ deEsserReductionDb.toFixed(1) }} dB</output>
              <input id="de-esser" v-model.number="deEsserReductionDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="saturation">{{ t("saturation") }} <InfoTip :text="t('saturationTip')" /></label>
              <output>{{ Math.round(saturationAmount * 100) }}%</output>
              <input id="saturation" v-model.number="saturationAmount" type="range" min="0" max="1" step="0.05" @input="activeIntent = 'Custom'" />
            </div>
          </fieldset>

          <fieldset class="advanced-dsp">
            <legend class="control-heading grouped-control-heading">
              <span>{{ t("transientControl") }} <InfoTip :text="t('transientControlTip')" /></span>
            </legend>
            <div class="mini-control">
              <label for="clipper-drive">{{ t("clipperDrive") }} <InfoTip :text="t('clipperDriveTip')" /></label>
              <output>{{ clipperDriveDb.toFixed(1) }} dB</output>
              <input id="clipper-drive" v-model.number="clipperDriveDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="limiter-lookahead">{{ t("limiterLookahead") }} <InfoTip :text="t('limiterLookaheadTip')" /></label>
              <output>{{ limiterLookaheadMs.toFixed(1) }} ms</output>
              <input id="limiter-lookahead" v-model.number="limiterLookaheadMs" type="range" min="0" max="10" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="limiter-release">{{ t("limiterRelease") }} <InfoTip :text="t('limiterReleaseTip')" /></label>
              <output>{{ limiterReleaseMs.toFixed(0) }} ms</output>
              <input id="limiter-release" v-model.number="limiterReleaseMs" type="range" min="10" max="500" step="10" @input="activeIntent = 'Custom'" />
            </div>
          </fieldset>

          <fieldset>
            <legend class="control-heading">
              <span>{{ t("aiAssistance") }} <InfoTip :text="t('aiAssistanceTip')" /></span>
            </legend>
            <button
              class="ai-assistance-toggle"
              type="button"
              :class="{ active: aiAssistEnabled }"
              :aria-pressed="aiAssistEnabled"
              @click="aiAssistEnabled = !aiAssistEnabled; activeIntent = 'Custom'"
            >
              <span>✦</span>
              <strong>{{ aiAssistEnabled ? t("aiEnabled") : t("aiDisabled") }}</strong>
              <small>{{ t("aiAssistanceSmall") }}</small>
            </button>
          </fieldset>

          <fieldset>
            <legend class="control-heading grouped-control-heading">
              <span>{{ t("safeguards") }} <InfoTip :text="t('safeguardsTip')" /></span>
            </legend>
            <div class="safeguard-grid">
              <button type="button" :class="{ active: extraHeadroom }" @click="toggleHeadroom" :title="t('extraHeadroomTip')">
                <span>◇</span><strong>{{ t("extraHeadroom") }}</strong><small>{{ t("extraHeadroomSmall") }}</small>
              </button>
              <button type="button" :class="{ active: gentleCorrection }" @click="toggleCorrection" :title="t('gentleCorrectionTip')">
                <span>↕</span><strong>{{ t("gentleCorrection") }}</strong><small>{{ t("gentleCorrectionSmall") }}</small>
              </button>
              <button type="button" :class="{ active: highResolution }" @click="toggleResolution" :title="t('highResolutionTip')">
                <span>✦</span><strong>{{ t("highResolution") }}</strong><small>{{ t("highResolutionSmall") }}</small>
              </button>
            </div>
          </fieldset>
          </div>
          </div>

          <div class="master-summary">
            <span>{{ t("activeProfile") }}</span>
            <strong>{{ activeIntentLabel }}</strong>
            <small>{{ t("outputSummary", { lufs: targetLufs.toFixed(1), ceiling: ceilingDbfs.toFixed(1), depth: bitDepth }) }}</small>
          </div>
          <button
            class="master-button"
            type="button"
            :disabled="submitting"
            @click="job.status === 'analyzed' ? startMasterDecision() : requestFinalRender()"
          >
            <span>{{ submitting ? t("mastering") : (locale === "fr" ? "Créer un nouveau master" : "Create a new master") }}</span>
            <b>→</b>
          </button>
          <button class="return-presets" type="button" @click="resetInteractiveSettings">
            ↺ {{ locale === "fr" ? "Réinitialiser et choisir un preset" : "Reset and choose a preset" }}
          </button>
        </aside>
      </form>

      <p v-if="error" class="alert error" role="alert"><span>!</span>{{ error }}</p>

      <section v-if="job" class="results" aria-live="polite">
        <div class="pipeline panel">
          <div class="panel-heading">
            <div><span class="step">03</span><h2>{{ t("processing") }}</h2></div>
            <span class="job-id">{{ progressPercent }}%</span>
          </div>
          <div class="pipeline-progress" :aria-label="`${progressPercent}%`">
            <i :style="{ width: `${progressPercent}%` }"></i>
            <b>{{ progressPercent }}%</b>
          </div>
          <ol>
            <li
              v-for="(stage, index) in pipelineStages"
              :key="stage.key"
              :class="{ done: currentStage > index, active: currentStage === index, failed: job.status === 'failed' && index === currentStage }"
            >
              <span>
                <i v-if="currentStage === index && !isTerminalStatus(job.status)" class="stage-loader"></i>
                <template v-else>{{ currentStage > index ? "✓" : index + 1 }}</template>
              </span>
              <strong>{{ stage.label }}</strong>
              <small>{{ currentStage > index ? "100%" : (currentStage === index ? `${progressPercent}%` : "0%") }}</small>
            </li>
          </ol>
          <div v-if="!isTerminalStatus(job.status)" class="progress-line"><i></i></div>
        </div>

        <AnalysisDashboard
          v-if="job.result"
          :result="job.result"
          :target-lufs="targetLufs"
          :ceiling-dbfs="ceilingDbfs"
          :maximum-gain-adjustment-db="maximumGainAdjustmentDb"
          :bit-depth="bitDepth"
          :locale="locale"
        />

        <div
          v-if="sourceUrl && job.preview_url && job.source_waveform && job.master_waveform"
          ref="beforeAfterAnchor"
          class="comparison-anchor"
        >
          <BeforeAfterPlayer
            :before-url="sourceUrl"
            :after-url="job.preview_url"
            :locale="locale"
            :before-waveform="job.source_waveform"
            :after-waveform="job.master_waveform"
            :before-spectrum="job.source_spectrum"
            :after-spectrum="job.master_spectrum"
            :before-level-timeline="job.source_level_timeline"
            :after-level-timeline="job.master_level_timeline"
          />
        </div>

        <div v-if="job.preview_url || job.initial_preview_url" class="final-render-actions panel">
          <button type="button" :disabled="submitting" @click="saveSettings">
            {{ locale === "fr" ? "Enregistrer les réglages" : "Save settings" }}
          </button>
          <p>{{ locale === "fr" ? "Ce master est immuable. Téléchargez-le puis continuez à régler depuis l’original." : "This master is immutable. Download it, then keep working from the original." }}</p>
        </div>

        <div v-if="findings.length" class="panel assistant-panel">
          <div class="assistant-intro">
            <span class="assistant-orb">✦</span>
            <div><p class="eyebrow">{{ t("assistant") }}</p><h2>{{ t("heard") }}</h2></div>
          </div>
          <ul>
            <li v-for="finding in findings" :key="finding.code">
              <span>↳</span>{{ finding.message }}
            </li>
          </ul>
        </div>

        <AiMasteringChanges
          v-if="aiAssistance"
          :assistance="aiAssistance"
          :locale="locale"
        />

        <div v-if="job.download_url" class="delivery panel">
          <div>
            <p class="eyebrow">{{ t("masterReady") }}</p>
            <h2>{{ t("finalWaiting") }}</h2>
            <p>{{ t("privateDownload", { depth: bitDepth }) }}</p>
          </div>
          <a class="download" :href="job.download_url">{{ t("download") }} <span>↓</span></a>
        </div>

        <p v-if="job.error_message" class="alert error"><span>!</span>{{ job.error_message }}</p>

        <button v-if="job.result" class="technical-toggle" type="button" @click="showTechnical = !showTechnical">
          {{ showTechnical ? t("hide") : t("show") }} {{ t("technicalJson") }}
        </button>
        <div v-if="showTechnical" class="technical-grid">
          <pre>{{ JSON.stringify(job.result, null, 2) }}</pre>
          <pre v-if="job.recommendation">{{ JSON.stringify(job.recommendation, null, 2) }}</pre>
          <pre v-if="job.mastering_result">{{ JSON.stringify(job.mastering_result, null, 2) }}</pre>
        </div>
      </section>
    </main>

    <footer><span>OPENMASTER · 2026</span><span>{{ t("footer") }}</span></footer>
  </div>
</template>
