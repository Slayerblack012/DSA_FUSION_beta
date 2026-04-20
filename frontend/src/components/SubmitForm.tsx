"use client";

import React, { useCallback } from "react";
import {
  Upload,
  BadgeCheck,
  FileCode2,
  ClipboardList,
  ShieldCheck,
  FileText,
  Trash2,
} from "lucide-react";
import { useDropzone, type FileRejection } from "react-dropzone";
import toast from "react-hot-toast";
import type { StudentInfo, SystemSettings } from "@/types";



interface SubmitFormProps {
  studentInfo: StudentInfo;
  setStudentInfo: React.Dispatch<React.SetStateAction<StudentInfo>>;
  files: File[];
  setFiles: React.Dispatch<React.SetStateAction<File[]>>;
  isSubmitting: boolean;
  settings: SystemSettings;
  onSubmit: () => Promise<void>;
  onNotify: (type: "success" | "error", message: string) => void;
  resultsHistory: unknown[];
  latest: unknown;
}

export const SubmitForm = ({
  studentInfo,
  setStudentInfo,
  files,
  setFiles,
  isSubmitting,
  settings,
  onSubmit,
  onNotify,
  resultsHistory,
  latest,
}: SubmitFormProps) => {
  const [assignmentCodes, setAssignmentCodes] = React.useState<string[]>([]);
  const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8000";
  const API_BASE_URL = RAW_API_BASE_URL.replace("localhost", "127.0.0.1");
  React.useEffect(() => {
    // Dùng biến API_BASE_URL để nó tự động đổi sang URL của Render khi deploy
    fetch(`${API_BASE_URL}/submissions/assignments/codes`)
      .then((res) => res.json())
      .then((data) => setAssignmentCodes(data))
      .catch(() => {});
}, []);
  const showFileToast = useCallback(
    (type: "success" | "error" | "warning", title: string, description: string) => {
      if (!settings.enableNotifications) return;
      toast.custom(
        (t) => (
          <div
            className={`${t.visible ? "animate-enter" : "animate-leave"} max-w-md w-full bg-white shadow-xl rounded-xl pointer-events-auto flex ring-1 ring-black ring-opacity-5 border-l-4 ${
              type === "success"
                ? "border-green-500"
                : type === "error"
                ? "border-red-500"
                : "border-yellow-500"
            }`}
          >
            <div className="flex-1 w-0 p-4">
              <div className="flex items-start">
                <div className="flex-shrink-0 pt-0.5">
                  {type === "success" ? (
                    <span className="h-10 w-10 text-green-500 bg-green-50 p-2 rounded-lg">✓</span>
                  ) : type === "error" ? (
                    <span className="h-10 w-10 text-red-500 bg-red-50 p-2 rounded-lg">✗</span>
                  ) : (
                    <span className="h-10 w-10 text-yellow-500 bg-yellow-50 p-2 rounded-lg">!</span>
                  )}
                </div>
                <div className="ml-3 flex-1">
                  <p className="text-sm font-bold text-gray-900">{title}</p>
                  <p className="mt-1 text-xs text-gray-500 leading-relaxed whitespace-pre-line">
                    {description}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex border-l border-gray-100">
              <button
                onClick={() => toast.dismiss(t.id)}
                className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-xs font-semibold text-gray-400 hover:text-gray-600 focus:outline-none"
              >
                Đóng
              </button>
            </div>
          </div>
        ),
        { duration: 5000 }
      );
    },
    [settings.enableNotifications]
  );

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const names = rejected
          .map((r) => r.file?.name)
          .slice(0, 2)
          .join(", ") + (rejected.length > 2 ? "..." : "");
        showFileToast(
          "error",
          "Tệp tin không hợp lệ",
          `Hệ thống từ chối: ${names}\nVui lòng dùng tệp bài nộp hợp lệ dưới 10MB.`
        );
      }

      if (accepted.length === 0) return;

      const emptyFiles = accepted.filter((f) => f.size === 0);
      const validFiles = accepted.filter((f) => f.size > 0);

      if (emptyFiles.length > 0) {
        const names =
          emptyFiles.map((f) => f.name).slice(0, 2).join(", ") +
          (emptyFiles.length > 2 ? "..." : "");
        showFileToast(
          "warning",
          "Phát hiện tệp nội dung trống",
          `${names} có kích thước 0 KB.\nVui lòng kiểm tra lại nội dung trước khi nộp.`
        );
      }

      if (validFiles.length > 0) {
        setFiles((prev) => [...prev, ...validFiles]);
        const details = validFiles
          .map((f) => `• ${f.name} (${(f.size / 1024).toFixed(1)} KB)`)
          .join("\n");
        showFileToast("success", `Đã ghi nhận ${validFiles.length} bài làm`, details);
      }
    },
    [showFileToast, setFiles]
  );

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: {
      "text/x-python": [".py"],
      "application/zip": [".zip"],
      "application/x-rar-compressed": [".rar"],
    },
    maxSize: 10 * 1024 * 1024,
  });

  const handleClearAllFiles = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.stopPropagation();
    if (files.length === 0) return;
    setFiles([]);
    onNotify("success", "Đã xóa toàn bộ tệp đã chọn.");
  };

  const handleRemoveSingleFile = (e: React.MouseEvent<HTMLButtonElement>, idx: number) => {
    e.stopPropagation();
    const target = files[idx];
    if (!target) return;
    setFiles((prev) => prev.filter((_, index) => index !== idx));
    onNotify("success", `Đã xóa tệp ${target.name}.`);
  };

  const handleValidate = () => {
    if (!studentInfo.id || !studentInfo.name) {
      onNotify("error", "Thông tin thí sinh (MSSV/Họ tên) không được để trống.");
      return;
    }
    if (files.length === 0) {
      onNotify("error", "Vui lòng tải lên ít nhất một tệp bài giải.");
      return;
    }
    onSubmit();
  };

  return (
    <div className="space-y-6 min-h-[calc(100vh-140px)] flex flex-col justify-center py-4">
      {/* Page Header */}
      <div className="rounded-2xl p-6 md:p-8 lg:p-9 relative overflow-hidden text-white brand-gradient shadow-[0_12px_30px_rgba(30,64,175,0.28)]">
        <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute right-8 top-1/2 -translate-y-1/2 opacity-[0.08] pointer-events-none hidden md:block">
          <div className="relative w-44 h-44">
            <FileCode2 className="absolute inset-0 w-44 h-44" />
            <Upload className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14" />
          </div>
        </div>
        <div className="relative">
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Nộp bài tập DSA</h1>
          <p className="text-sm md:text-base text-blue-100 mt-2 max-w-xl">
            Kéo thả tệp bài làm và nhận kết quả đánh giá tự động kèm nhận xét chi tiết.
          </p>
          <div className="grid grid-cols-3 gap-3 mt-6">
            {[
              { k: "Lượt nộp", v: String(resultsHistory.length) },
              {
                k: "Độ trễ TB",
                v: latest
                  ? `${(
                      ((latest as any).totalTimeMs || (latest as any).total_time_ms || 0) / 1000
                    ).toFixed(1)}s`
                  : "-",
              },
              {
                k: "Điểm gần nhất",
                v: latest && ((latest as any).totalScore ?? (latest as any).total_score) != null ? ((latest as any).totalScore ?? (latest as any).total_score)?.toFixed(1) : "-",
              },
            ].map((metric) => (
              <div
                key={metric.k}
                className="rounded-lg bg-white/10 border border-white/20 px-3 py-2"
              >
                <p className="text-[11px] text-blue-100">{metric.k}</p>
                <p className="text-lg font-semibold leading-tight mt-1">{metric.v}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-5 lg:gap-6 items-stretch">
        {/* Left – Form */}
        <div className="col-span-12 lg:col-span-6 space-y-5">
          <div className="card-elevated p-6 lg:p-7 min-h-[300px]">
            <h2 className="label-sm mb-5 flex items-center gap-2">
              <BadgeCheck className="w-4 h-4 text-blue-600" /> Thông tin sinh viên
            </h2>
            <div className="space-y-4">
              <div>
                <label className="label">Mã số sinh viên</label>
                <input
                  type="text"
                  value={studentInfo.id}
                  onChange={(e) => setStudentInfo({ ...studentInfo, id: e.target.value })}
                  placeholder="VD: 122000xxx"
                  className="input"
                />
              </div>
              <div>
                <label className="label">Họ và tên</label>
                <input
                  type="text"
                  value={studentInfo.name}
                  onChange={(e) => setStudentInfo({ ...studentInfo, name: e.target.value })}
                  placeholder="VD: Nguyễn Văn A"
                  className="input"
                />
              </div>
              <div>
              <label className="label text-blue-600 font-bold">Chọn mã bài tập</label>
              <select
                value={(studentInfo as any).assignmentCode || ""}
                onChange={(e) => setStudentInfo({ ...studentInfo, ["assignmentCode" as any]: e.target.value })}
                className="input appearance-none bg-white border-blue-200 focus:ring-blue-600 cursor-pointer"
              >
                <option value="">-- Click để chọn mã bài tập --</option>
                {assignmentCodes.map((code) => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
            </div>
            </div>
          </div>

          <div className="card p-5 lg:p-6 min-h-[210px]">
            <h2 className="label-sm mb-4">Thông tin bài tập</h2>
            <div className="rounded-lg border border-gray-100 bg-white divide-y divide-gray-100">
              {[
                { k: "Loại bài nộp", v: "Bài tập lập trình", icon: FileCode2 },
                { k: "Chủ đề", v: "Thuật toán", icon: ClipboardList },
                { k: "Đánh giá", v: "Tính đúng và hiệu quả", icon: ShieldCheck },
              ].map((info, i) => (
                <div
                  key={i}
                  className="grid grid-cols-[minmax(0,200px)_1fr] items-center gap-4 px-3 py-3 text-[13px]"
                >
                  <span className="flex items-center gap-2 text-gray-500">
                    <info.icon className="w-3.5 h-3.5" /> {info.k}
                  </span>
                  <span className="font-medium text-gray-800 text-left">{info.v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right – Upload */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-5">
          <div
            {...getRootProps()}
            className="flex-1 card border-dashed border-2 bg-white flex flex-col items-center justify-center p-8 md:p-12 lg:p-14 min-h-[360px] lg:min-h-[430px] cursor-pointer group hover:border-blue-300 hover:bg-blue-50/30 transition-all"
          >
            <input {...getInputProps()} />
            <div className="w-14 h-14 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-center mb-6 group-hover:bg-blue-600 group-hover:border-blue-600 transition-all">
              <Upload className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
            </div>
            <p className="text-base font-semibold text-gray-800 mb-1">
              Kéo thả hoặc nhấn để chọn tệp
            </p>
            <p className="text-sm text-gray-400">
              Hỗ trợ tệp bài nộp hợp lệ — tối đa 10MB
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
              <span className="badge badge-blue">Kiểm tra tự động</span>
              <span className="badge badge-neutral">Môi trường an toàn</span>
              <span className="badge badge-neutral">Báo cáo chi tiết</span>
            </div>

            {files.length > 0 && (
              <div className="mt-8 w-full max-w-md">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[12px] font-semibold text-gray-500">
                    {files.length} tệp đã chọn
                  </span>
                  <button
                    onClick={handleClearAllFiles}
                    className="text-[12px] font-medium text-red-500 hover:text-red-700"
                  >
                    Xóa tất cả
                  </button>
                </div>
                <div className="max-h-48 overflow-y-auto thin-scroll space-y-2">
                  {files.map((file, i) => (
                    <div
                      key={i}
                      className="bg-white border border-gray-100 rounded-lg px-4 py-3 flex items-center justify-between hover:border-gray-200 transition-colors"
                    >
                      <div className="flex items-center gap-3 truncate">
                        <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                        <span className="text-sm text-gray-700 truncate">{file.name}</span>
                        <span className="text-[11px] text-gray-400 shrink-0">
                          {(file.size / 1024).toFixed(0)} KB
                        </span>
                      </div>
                      <button
                        onClick={(e) => handleRemoveSingleFile(e, i)}
                        className="text-gray-300 hover:text-red-500 p-0.5"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="sticky bottom-2 pt-2 bg-gradient-to-t from-[#fffbf7] via-[#fffbf7]/90 to-transparent">
            <button
              onClick={handleValidate}
              disabled={isSubmitting || files.length === 0}
              className="btn-primary w-full h-12 lg:h-14 text-[15px]"
            >
              Nộp bài và chấm điểm
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
