"use client";

import React, { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import toast, { Toaster } from "react-hot-toast";

import {
  AppHeader,
  AppSidebar,
  ConfirmDialog,
  GradingOverlay,
  MobileBottomNav,
  MobileNav,
  ResultsTab,
  SettingsTab,
  SubmitForm,
  SystemToast,
} from "@/components";
import { submitAiOnlyGrading } from "@/lib/submissionClient";
import type { AppTab, ConfirmDialogState, ResultRecord, StudentInfo, SystemSettings } from "@/types";

const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8000";
const API_BASE_URL = RAW_API_BASE_URL.replace("http://localhost:", "http://127.0.0.1:").replace("https://localhost:", "https://127.0.0.1:");
const SUBMISSION_BASE_URLS = [API_BASE_URL];
const TOAST_DURATION_MS = 5000;
const SETTINGS_STORAGE_KEY = "edu_system_settings_v2";
const RESULTS_STORAGE_KEY = "edu_results_v9";
const STUDENT_STORAGE_KEY = "edu_student_v1";
const DEBUG_SUBMISSION_NETWORK = process.env.NODE_ENV !== "production";

const DEFAULT_SYSTEM_SETTINGS: SystemSettings = {
  requestTimeoutMs: 120000,
  autoOpenHistory: true,
  enableNotifications: true,
  rememberStudent: true,
};

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
    open: false,
    title: "Xác nhận thao tác",
    message: "",
    confirmText: "Đồng ý",
    onConfirm: null,
  });

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 800);
    const savedResults = localStorage.getItem(RESULTS_STORAGE_KEY);
    const savedStudent = localStorage.getItem(STUDENT_STORAGE_KEY);
    const savedSettings = localStorage.getItem(SETTINGS_STORAGE_KEY);

    let resolvedSettings = DEFAULT_SYSTEM_SETTINGS;
    if (savedSettings) {
      try {
        const parsed = { ...DEFAULT_SYSTEM_SETTINGS, ...JSON.parse(savedSettings) };
        resolvedSettings = {
          ...parsed,
          requestTimeoutMs: Math.max(120000, Number(parsed.requestTimeoutMs) || 120000),
        };
      } catch {
        resolvedSettings = DEFAULT_SYSTEM_SETTINGS;
      }
    }

    setSystemSettings(resolvedSettings);
    setSettingsLastUpdated(new Date().toLocaleString("vi-VN"));

    if (savedResults) {
      try {
        setResultsHistory(JSON.parse(savedResults));
      } catch {
        // ignore malformed local cache
      }
    }

    if (savedStudent && resolvedSettings.rememberStudent) {
      try {
        setStudentInfo(JSON.parse(savedStudent));
      } catch {
        // ignore malformed local cache
      }
    }

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    localStorage.setItem(RESULTS_STORAGE_KEY, JSON.stringify(resultsHistory));
  }, [resultsHistory]);

  useEffect(() => {
    if (systemSettings.rememberStudent) {
      localStorage.setItem(STUDENT_STORAGE_KEY, JSON.stringify(studentInfo));
      return;
    }
    localStorage.removeItem(STUDENT_STORAGE_KEY);
  }, [studentInfo, systemSettings.rememberStudent]);

  useEffect(() => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(systemSettings));
    setSettingsLastUpdated(new Date().toLocaleString("vi-VN"));
  }, [systemSettings]);

  const updateSystemSetting = <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => {
    setSystemSettings((prev) => ({ ...prev, [key]: value }));
  };

  const notify = useCallback((type: "success" | "error" | "destructive", message: string) => {
    if (!systemSettings.enableNotifications) return;
    const variant = type === "success" ? "default" : "destructive";
    toast.custom((toastState) => <SystemToast t={toastState} message={message} variant={variant} />, {
      duration: TOAST_DURATION_MS,
      position: "top-right",
    });
  }, [systemSettings.enableNotifications]);

  const openConfirmDialog = (title: string, message: string, confirmText: string, onConfirm: () => void) => {
    setConfirmDialog({ open: true, title, message, confirmText, onConfirm });
  };

  const closeConfirmDialog = () => {
    setConfirmDialog((prev) => ({ ...prev, open: false, onConfirm: null }));
  };

  const clearHistory = () => openConfirmDialog(
    "Xóa lịch sử kết quả",
    "Bạn có chắc muốn xóa toàn bộ lịch sử kết quả trên trình duyệt này không?",
    "Xóa lịch sử",
    () => {
      setResultsHistory([]);
      notify("success", "Đã xóa lịch sử kết quả trên trình duyệt.");
    },
  );

  const resetSession = () => openConfirmDialog(
    "Reset phiên hiện tại",
    "Hành động này sẽ xóa file tải lên và thông tin sinh viên đang nhập.",
    "Reset phiên",
    () => {
      setFiles([]);
      setStudentInfo({ id: "", name: "" });
      notify("success", "Đã reset phiên làm việc.");
    },
  );

  const exportSystemSettings = () => {
    const blob = new Blob([JSON.stringify(systemSettings, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "dsa-fusion-settings.json";
    anchor.click();
    URL.revokeObjectURL(url);
    notify("success", "Đã xuất tệp cài đặt hệ thống.");
  };

  const importSystemSettingsFromFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const parsed = JSON.parse(await file.text()) as Partial<SystemSettings>;
      setSystemSettings({
        requestTimeoutMs: typeof parsed.requestTimeoutMs === "number" ? Math.max(120000, parsed.requestTimeoutMs) : 120000,
        autoOpenHistory: typeof parsed.autoOpenHistory === "boolean" ? parsed.autoOpenHistory : true,
        enableNotifications: typeof parsed.enableNotifications === "boolean" ? parsed.enableNotifications : true,
        rememberStudent: typeof parsed.rememberStudent === "boolean" ? parsed.rememberStudent : true,
      });
      notify("success", "Đã nhập cấu hình hệ thống từ tệp JSON.");
    } catch {
      notify("error", "Không thể đọc tệp cấu hình. Vui lòng kiểm tra định dạng JSON.");
    } finally {
      event.target.value = "";
    }
  };

  const restoreDefaultSettings = () => openConfirmDialog(
    "Khôi phục cài đặt",
    "Bạn có chắc muốn khôi phục toàn bộ cài đặt mặc định không?",
    "Khôi phục",
    () => {
      setSystemSettings(DEFAULT_SYSTEM_SETTINGS);
      notify("success", "Đã khôi phục cài đặt mặc định.");
    },
  );

  const handleSubmit = async () => {
    if (!studentInfo.id || !studentInfo.name) {
      notify("error", "Thông tin thí sinh (MSSV/Họ tên) không được để trống.");
      return;
    }
    if (files.length === 0) {
      notify("error", "Vui lòng tải lên ít nhất một tệp bài giải.");
      return;
    }

    setIsSubmitting(true);
    const submissionPromise = async () => {
      const { data, record } = await submitAiOnlyGrading({
        apiBaseUrls: SUBMISSION_BASE_URLS,
        files,
        studentInfo,
        settings: systemSettings,
        debug: DEBUG_SUBMISSION_NETWORK,
      });
      setResultsHistory((prev) => [record, ...prev]);
      if (systemSettings.autoOpenHistory) setActiveTab("history");
      setFiles([]);
      return data;
    };

    if (systemSettings.enableNotifications) {
      toast.promise(submissionPromise(), {
        loading: "AI đang đọc bài, đối chiếu rubric và tạo feedback chi tiết...",
        success: (data) => (
          <div className="flex flex-col gap-1.5 p-1">
            <span className="font-black text-[14px] text-emerald-700 uppercase tracking-tight">Chấm điểm hoàn tất</span>
            <div className="my-0.5 h-px w-full bg-emerald-100" />
            <span className="text-[13px] font-bold text-slate-700">
              Điểm tổng kết: <span className="text-lg text-emerald-600">{data.total_score?.toFixed(1) ?? "?"}</span>/10
            </span>
          </div>
        ),
        error: (error) => (
          <div className="flex flex-col gap-1 p-1">
            <span className="font-black text-[14px] uppercase tracking-tight text-rose-700">Lỗi chấm điểm</span>
            <span className="text-[12px] font-medium leading-snug text-slate-500">{error.message}</span>
          </div>
        ),
      }).finally(() => setIsSubmitting(false));
      return;
    }

    submissionPromise()
      .catch((error: Error) => window.alert(`Lỗi: ${error.message}`))
      .finally(() => setIsSubmitting(false));
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-white">
        <div className="mb-5 h-9 w-9 animate-spin rounded-full border-[3px] border-gray-100 border-t-blue-600" />
        <p className="text-sm font-medium text-gray-500">Đang khởi tạo hệ thống...</p>
      </div>
    );
  }

  const latest = resultsHistory[0] ?? null;

  return (
    <div className="app-bg flex min-h-screen flex-col font-sans text-gray-900">
      <Toaster position="top-right" toastOptions={{ duration: TOAST_DURATION_MS }} />
      <AnimatePresence>{isSubmitting && <GradingOverlay />}</AnimatePresence>

      <AppHeader activeTab={activeTab} setActiveTab={setActiveTab} studentName={studentInfo.name} />
      <MobileNav activeTab={activeTab} setActiveTab={setActiveTab} />

      <div className="flex flex-1 overflow-hidden">
        <AppSidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="thin-scroll flex-1 overflow-y-auto pb-20 md:pb-8 lg:ml-56">
          <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 2xl:px-12">
            <AnimatePresence mode="wait">
              {activeTab === "submit" && (
                <motion.div
                  key="submit"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  <SubmitForm
                    studentInfo={studentInfo}
                    setStudentInfo={setStudentInfo}
                    files={files}
                    setFiles={setFiles}
                    isSubmitting={isSubmitting}
                    settings={systemSettings}
                    onSubmit={handleSubmit}
                    onNotify={notify}
                    openConfirmDialog={openConfirmDialog}
                    resultsHistory={resultsHistory}
                    latest={latest}
                  />
                </motion.div>
              )}

              {activeTab === "history" && (
                <motion.div
                  key="history"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  <ResultsTab latest={latest} studentInfo={studentInfo} onBackToSubmit={() => setActiveTab("submit")} />
                </motion.div>
              )}

              {activeTab === "settings" && (
                <motion.div
                  key="settings"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                >
                  <SettingsTab
                    settings={systemSettings}
                    updateSetting={updateSystemSetting}
                    settingsLastUpdated={settingsLastUpdated}
                    onClearHistory={clearHistory}
                    onExportSettings={exportSystemSettings}
                    onImportSettings={importSystemSettingsFromFile}
                    onRestoreDefaults={restoreDefaultSettings}
                    onResetSession={resetSession}
                  />
                </motion.div>
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
