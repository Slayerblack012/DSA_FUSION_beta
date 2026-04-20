"use client";

import React, { useState, useEffect, useCallback } from "react";
import { AnimatePresence } from "framer-motion";
import toast, { Toaster } from "react-hot-toast";
import type { AppTab, ResultRecord, SystemSettings, ConfirmDialogState, StudentInfo } from "@/types";
import {
  GradingOverlay,
  AppHeader,
  MobileNav,
  MobileBottomNav,
  AppSidebar,
  SubmitForm,
  ResultsTab,
  SettingsTab,
  ConfirmDialog,
  SystemToast,
} from "@/components";

// ============================================================
// Constants
// ============================================================
const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8000";
const API_BASE_URL = RAW_API_BASE_URL.replace("http://localhost:", "http://127.0.0.1:").replace("https://localhost:", "https://127.0.0.1:");
const SUBMISSION_BASE_URLS = [API_BASE_URL];
const PREFERRED_SUBMISSION_ENDPOINT_KEY = "edu_preferred_submission_endpoint_v1";
const TOAST_DURATION_MS = 5000;
const SETTINGS_STORAGE_KEY = "edu_system_settings_v2";
const DEBUG_SUBMISSION_NETWORK = process.env.NODE_ENV !== "production";

const DEFAULT_SYSTEM_SETTINGS: SystemSettings = {
  requestTimeoutMs: 120000,
  autoOpenHistory: true,
  enableNotifications: true,
  rememberStudent: true,
};

// ============================================================
// Endpoint caching helpers
// ============================================================
const normalizeBaseUrl = (base: string) => base.replace(/\/$/, "");

const failedEndpointsCache = new Set<string>();
const cacheExpiryTime = 5 * 60 * 1000;
let cacheClearedAt = Date.now();

const clearExpiredCache = () => {
  if (Date.now() - cacheClearedAt > cacheExpiryTime) {
    failedEndpointsCache.clear();
    cacheClearedAt = Date.now();
  }
};

const buildSubmissionEndpoints = () => {
  const candidates: string[] = [];
  clearExpiredCache();
  for (const rawBase of SUBMISSION_BASE_URLS) {
    const base = normalizeBaseUrl(rawBase);
    if (!base) { candidates.push("/submissions/"); continue; }
    candidates.push(`${base}/submissions/`);
    candidates.push(`${base}/api/submissions/`);
  }
  const filtered = candidates.filter((endpoint) => !failedEndpointsCache.has(endpoint));
  return filtered.length > 0 ? Array.from(new Set(filtered)) : Array.from(new Set(candidates));
};

const markEndpointFailed = (endpoint: string) => {
  clearExpiredCache();
  failedEndpointsCache.add(endpoint);
};

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const fetchWithTimeout = async (input: RequestInfo | URL, init: RequestInit, timeoutMs: number) => {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try { return await fetch(input, { ...init, signal: controller.signal }); }
  finally { window.clearTimeout(timeoutId); }
};

const isLikelyBackendNotFound = (endpoint: string, status: number) =>
  endpoint.startsWith("/") && (status === 404 || status === 405);

const getPreferredEndpoint = () => {
  try { return localStorage.getItem(PREFERRED_SUBMISSION_ENDPOINT_KEY) || ""; } catch { return ""; }
};

const savePreferredEndpoint = (endpoint: string) => {
  try { localStorage.setItem(PREFERRED_SUBMISSION_ENDPOINT_KEY, endpoint); } catch { /* ignore */ }
};

const normalizeSubmissionError = (error: unknown, timeoutMs: number) => {
  if (error instanceof DOMException && error.name === "AbortError") {
    return `Hết thời gian chờ (${timeoutMs}ms). Kiểm tra backend hoặc tăng timeout trong Cài đặt.`;
  }
  if (error instanceof TypeError) {
    const message = error.message.toLowerCase();
    if (message.includes("failed to fetch") || message.includes("networkerror") || message.includes("load failed")) {
      return "Không thể kết nối máy chủ chấm điểm. Kiểm tra backend tại http://localhost:8000.";
    }
  }
  if (error instanceof Error) return error.message;
  return "Lỗi không xác định khi xử lý bài nộp.";
};

// ============================================================
// Main component (thin orchestrator — ~350 lines)
// ============================================================
export default function EduPortal() {
  const [studentInfo, setStudentInfo] = useState<StudentInfo>({ id: "", name: "" });
  const [files, setFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<AppTab>("submit");
  const [resultsHistory, setResultsHistory] = useState<ResultRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [systemSettings, setSystemSettings] = useState<SystemSettings>(DEFAULT_SYSTEM_SETTINGS);
  const [settingsLastUpdated, setSettingsLastUpdated] = useState<string>(new Date().toLocaleString("vi-VN"));
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false, title: "Xác nhận thao tác", message: "", confirmText: "Đồng ý", onConfirm: null,
  });

  // ---- Persistence ----
  useEffect(() => {
    const t = setTimeout(() => setIsLoading(false), 800);
    const saved = localStorage.getItem("edu_results_v9");
    const savedStudent = localStorage.getItem("edu_student_v1");
    const savedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);
    let resolvedSettings = DEFAULT_SYSTEM_SETTINGS;

    if (savedSettings) {
      try {
        const parsed = { ...DEFAULT_SYSTEM_SETTINGS, ...JSON.parse(savedSettings) };
        resolvedSettings = { ...parsed, requestTimeoutMs: Math.max(120000, Number(parsed.requestTimeoutMs) || 120000) };
        setSettingsLastUpdated(new Date().toLocaleString("vi-VN"));
      } catch { /* ignore */ }
    }
    setSystemSettings(resolvedSettings);
    if (saved) { try { setResultsHistory(JSON.parse(saved)); } catch { /* ignore */ } }
    if (savedStudent && resolvedSettings.rememberStudent) {
      try { setStudentInfo(JSON.parse(savedStudent)); } catch { /* ignore */ }
    }
    return () => clearTimeout(t);
  }, []);

  useEffect(() => { localStorage.setItem("edu_results_v9", JSON.stringify(resultsHistory)); }, [resultsHistory]);

  useEffect(() => {
    if (systemSettings.rememberStudent) { localStorage.setItem("edu_student_v1", JSON.stringify(studentInfo)); return; }
    localStorage.removeItem("edu_student_v1");
  }, [studentInfo, systemSettings.rememberStudent]);

  useEffect(() => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(systemSettings));
    setSettingsLastUpdated(new Date().toLocaleString("vi-VN"));
  }, [systemSettings]);

  // ---- Helpers ----
  const updateSystemSetting = <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => {
    setSystemSettings((prev) => ({ ...prev, [key]: value }));
  };

  const notify = useCallback((type: "success" | "error", message: string) => {
    if (!systemSettings.enableNotifications) return;
    toast.custom((t) => <SystemToast t={t} message={message} />, {
      duration: 5000,
      position: "top-right"
    });
  }, [systemSettings.enableNotifications]);

  const openConfirmDialog = (title: string, message: string, confirmText: string, onConfirm: () => void) => {
    setConfirmDialog({ open: true, title, message, confirmText, onConfirm });
  };

  const closeConfirmDialog = () => setConfirmDialog((prev) => ({ ...prev, open: false, onConfirm: null }));

  // ---- Actions ----
  const clearHistory = () => openConfirmDialog("Xóa lịch sử kết quả", "Bạn có chắc muốn xóa toàn bộ lịch sử kết quả trên trình duyệt này không?", "Xóa lịch sử", () => {
    setResultsHistory([]); notify("success", "Đã xóa lịch sử kết quả trên trình duyệt.");
  });

  const resetSession = () => openConfirmDialog("Reset phiên hiện tại", "Hành động này sẽ xóa file tải lên và thông tin sinh viên đang nhập.", "Reset phiên", () => {
    setFiles([]); setStudentInfo({ id: "", name: "" }); notify("success", "Đã reset phiên làm việc.");
  });

  const exportSystemSettings = () => {
    const blob = new Blob([JSON.stringify(systemSettings, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = "dsa-fusion-settings.json"; a.click(); URL.revokeObjectURL(url);
    notify("success", "Đã xuất tệp cài đặt hệ thống.");
  };

  const importSystemSettingsFromFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as Partial<SystemSettings>;
      setSystemSettings({
        requestTimeoutMs: typeof parsed.requestTimeoutMs === "number" ? Math.max(120000, parsed.requestTimeoutMs) : 120000,
        autoOpenHistory: typeof parsed.autoOpenHistory === "boolean" ? parsed.autoOpenHistory : true,
        enableNotifications: typeof parsed.enableNotifications === "boolean" ? parsed.enableNotifications : true,
        rememberStudent: typeof parsed.rememberStudent === "boolean" ? parsed.rememberStudent : true,
      });
      notify("success", "Đã nhập cấu hình hệ thống từ tệp JSON.");
    } catch { notify("error", "Không thể đọc tệp cấu hình. Vui lòng kiểm tra định dạng JSON."); }
    finally { event.target.value = ""; }
  };

  const restoreDefaultSettings = () => openConfirmDialog("Khôi phục cài đặt", "Bạn có chắc muốn khôi phục toàn bộ cài đặt mặc định không?", "Khôi phục", () => {
    setSystemSettings(DEFAULT_SYSTEM_SETTINGS); notify("success", "Đã khôi phục cài đặt mặc định.");
  });

  // ---- Submit handler ----
  const handleSubmit = async () => {
    if (!studentInfo.id || !studentInfo.name) { notify("error", "Thông tin thí sinh (MSSV/Họ tên) không được để trống."); return; }
    if (files.length === 0) { notify("error", "Vui lòng tải lên ít nhất một tệp bài giải."); return; }

    setIsSubmitting(true);
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("student_id", studentInfo.id);
    form.append("student_name", studentInfo.name);
    form.append("assignment_code", (studentInfo as any).assignmentCode || "");
    form.append("topic", "Thuật toán");
    const idempotencyKey = `${studentInfo.id}:${Date.now()}:${files.map((f) => f.name).join("|")}`;
    const submissionPromise = async () => {
      const submissionEndpoints = buildSubmissionEndpoints();
      const preferred = getPreferredEndpoint();
      const endpointQueue = preferred ? [preferred, ...submissionEndpoints.filter((e) => e !== preferred)] : submissionEndpoints;
      const perAttemptTimeoutMs = Math.max(8000, Math.min(30000, Math.floor(systemSettings.requestTimeoutMs / 3)));

      try {
        let lastNetworkError: unknown = null;
        let lastServerError: unknown = null;

        for (const endpoint of endpointQueue) {
          for (let attempt = 1; attempt <= 2; attempt++) {
            try {
              if (DEBUG_SUBMISSION_NETWORK) console.info(`[submit] attempt ${attempt}/2 -> ${endpoint}`);
              const res = await fetchWithTimeout(endpoint, { method: "POST", body: form, headers: { "Idempotency-Key": idempotencyKey } }, perAttemptTimeoutMs);
              if (!res.ok) { if (isLikelyBackendNotFound(endpoint, res.status)) break; const errData = await res.json().catch(() => null); throw new Error(errData?.detail || `Lỗi máy chủ (HTTP ${res.status})`); }

              const data = await res.json();
              if (DEBUG_SUBMISSION_NETWORK) console.info(`[submit] success via ${endpoint}`);
              savePreferredEndpoint(endpoint); failedEndpointsCache.clear();

              const firstResult = (data.results && data.results[0]) || {};
              const record: ResultRecord = {
                id: "EDU-" + Math.random().toString(36).substr(2, 6).toUpperCase(),
                studentId: data.student_id ?? firstResult.student_id ?? studentInfo.id, 
                studentName: data.student_name ?? firstResult.student_name ?? studentInfo.name,
                totalScore: data.total_score ?? (data.summary?.avg_score) ?? firstResult.total_score ?? 0,
                fileEvaluations: (data.file_evaluations || data.results || []).map((fe: any) => ({
                  fileName: fe.filename || fe.file_name || fe.fileName || "unknown.py", 
                  score: fe.total_score ?? fe.score ?? 0,
                  feedbacks: fe.feedbacks || (fe.feedback ? [fe.feedback] : []), 
                  aiAdvice: fe.reasoning || fe.ai_advice || fe.aiAdvice,
                  optimizedCode: fe.optimized_code || fe.optimizedCode, 
                  timeMs: (fe.time_used ? fe.time_used * 1000 : 0) || fe.time_ms || fe.timeMs || 0,
                  agentTrace: fe.agent_trace || fe.agentTrace, 
                  scoreProof: fe.score_proof || fe.scoreProof,
                  criteriaScores: fe.criteria_scores || fe.criteriaScores,
                  rubricSnapshot: fe.rubric_snapshot || fe.rubricSnapshot
                })),
                overallAiSummary: data.overall_ai_summary || data.overallAiSummary,
                timestamp: new Date().toLocaleString("vi-VN"),
                totalTimeMs: data.total_time_ms ?? data.totalTimeMs ?? (data.summary && parseFloat(data.summary.total_time) * 1000) ?? 0,
              };
              setResultsHistory((prev) => [record, ...prev]);
              if (systemSettings.autoOpenHistory) setActiveTab("history");
              setFiles([]);
              return data;
            } catch (error: unknown) {
              if (DEBUG_SUBMISSION_NETWORK) console.warn(`[submit] failure via ${endpoint}`, error);
              if (error instanceof DOMException && error.name === "AbortError") { markEndpointFailed(endpoint); lastNetworkError = error; }
              else if (error instanceof TypeError) { markEndpointFailed(endpoint); lastNetworkError = error; }
              else { lastServerError = error; break; }
              if (attempt < 2) await delay(350 * attempt);
            }
          }
        }
        throw lastNetworkError || lastServerError || new Error("Không thể kết nối máy chủ chấm điểm.");
      } catch (error: unknown) { throw new Error(normalizeSubmissionError(error, systemSettings.requestTimeoutMs)); }
    };

    if (systemSettings.enableNotifications) {
      toast.promise(submissionPromise(), {
        loading: "Đang thẩm định bài giải...",
        success: (data) => (<div className="flex flex-col gap-1"><span className="font-bold">Chấm điểm hoàn tất!</span><span className="text-xs opacity-80">Điểm: {data.total_score?.toFixed(1) ?? "?"}/10</span></div>),
        error: (err) => (<div className="flex flex-col gap-1"><span className="font-bold">Lỗi xử lý</span><span className="text-xs opacity-80">{err.message}</span></div>),
      }).finally(() => setIsSubmitting(false));
      return;
    }

    submissionPromise().catch((err: Error) => window.alert(`Lỗi: ${err.message}`)).finally(() => setIsSubmitting(false));
  };

  // ---- Loading ----
  if (isLoading) return (<div className="fixed inset-0 bg-white z-[100] flex flex-col items-center justify-center"><div className="w-9 h-9 border-[3px] border-gray-100 border-t-blue-600 rounded-full animate-spin mb-5" /><p className="text-sm font-medium text-gray-500">Đang khởi tạo hệ thống...</p></div>);

  const latest = resultsHistory[0] ?? null;

  // ---- Render ----
  return (
    <div className="min-h-screen app-bg text-gray-900 flex flex-col font-sans">
      <Toaster position="top-right" toastOptions={{ duration: TOAST_DURATION_MS }} />
      <AnimatePresence>{isSubmitting && <GradingOverlay />}</AnimatePresence>

      <AppHeader activeTab={activeTab} setActiveTab={setActiveTab} studentName={studentInfo.name} />
      <MobileNav activeTab={activeTab} setActiveTab={setActiveTab} />

      <div className="flex-1 flex overflow-hidden">
        <AppSidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 overflow-y-auto thin-scroll pb-20 md:pb-8 lg:ml-56">
          <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 2xl:px-12">
            <AnimatePresence mode="wait">
              {activeTab === "submit" && (
                <SubmitForm key="submit" studentInfo={studentInfo} setStudentInfo={setStudentInfo}
                  files={files} setFiles={setFiles} isSubmitting={isSubmitting} settings={systemSettings}
                  onSubmit={handleSubmit} onNotify={notify} resultsHistory={resultsHistory} latest={latest} />
              )}
              {activeTab === "history" && (
                <ResultsTab key="history" latest={latest} studentInfo={studentInfo} onBackToSubmit={() => setActiveTab("submit")} />
              )}
              {activeTab === "settings" && (
                <SettingsTab key="settings" settings={systemSettings} updateSetting={updateSystemSetting}
                  settingsLastUpdated={settingsLastUpdated} onClearHistory={clearHistory}
                  onExportSettings={exportSystemSettings} onImportSettings={importSystemSettingsFromFile}
                  onRestoreDefaults={restoreDefaultSettings} onResetSession={resetSession} />
              )}
            </AnimatePresence>
          </div>
        </main>
      </div>

      <MobileBottomNav activeTab={activeTab} setActiveTab={setActiveTab} />
      <ConfirmDialog dialog={confirmDialog} onClose={closeConfirmDialog} onConfirm={() => confirmDialog.onConfirm?.()} />
    </div>
  );
}
