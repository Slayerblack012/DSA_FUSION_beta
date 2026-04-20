"use client";

import React, { useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  BadgeCheck,
  FileCode2,
  ClipboardList,
  ShieldCheck,
  FileText,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { useDropzone, type FileRejection } from "react-dropzone";
import toast from "react-hot-toast";
import { SystemToast } from "./SystemToast";
import type { StudentInfo, SystemSettings } from "@/types";



interface SubmitFormProps {
  studentInfo: StudentInfo;
  setStudentInfo: React.Dispatch<React.SetStateAction<StudentInfo>>;
  files: File[];
  setFiles: React.Dispatch<React.SetStateAction<File[]>>;
  isSubmitting: boolean;
  settings: SystemSettings;
  onSubmit: () => Promise<void>;
  onNotify: (type: "success" | "error" | "destructive", message: string) => void;
  openConfirmDialog: (title: string, message: string, confirmText: string, onConfirm: () => void) => void;
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
  openConfirmDialog,
  resultsHistory,
  latest,
}: SubmitFormProps) => {
  const [assignmentCodes, setAssignmentCodes] = React.useState<string[]>([]);
  const [selectedAssignmentDetail, setSelectedAssignmentDetail] = React.useState<any>(null);
  const [isLoadingDetail, setIsLoadingDetail] = React.useState(false);
  const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8000";
  const API_BASE_URL = RAW_API_BASE_URL.replace("localhost", "127.0.0.1");
  React.useEffect(() => {
    // Dùng biến API_BASE_URL để nó tự động đổi sang URL của Render khi deploy
    fetch(`${API_BASE_URL}/submissions/assignments/codes`)
      .then((res) => res.json())
      .then((data) => setAssignmentCodes(data))
      .catch(() => {});
  }, []);

  React.useEffect(() => {
    const code = (studentInfo as any).assignmentCode;
    if (!code) {
      setSelectedAssignmentDetail(null);
      return;
    }

    setIsLoadingDetail(true);
    fetch(`${API_BASE_URL}/submissions/assignments/${code}`)
      .then((res) => res.json())
      .then((data) => {
        setSelectedAssignmentDetail(data);
      })
      .catch(() => {
        setSelectedAssignmentDetail(null);
      })
      .finally(() => {
        setIsLoadingDetail(false);
      });
  }, [studentInfo, API_BASE_URL]);
  const showFileToast = useCallback(
    (type: "success" | "error" | "warning", title: string, description: string) => {
      if (!settings.enableNotifications) return;
      const variant = type === "error" ? "destructive" : type === "warning" ? "destructive" : "default";
      toast.custom((t) => <SystemToast t={t} message={description} variant={variant} />, {
        duration: 5000,
        position: "top-right"
      });
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
    
    openConfirmDialog(
      "Thu hồi toàn bộ", 
      "Bạn có chắc chắn muốn xóa toàn bộ danh sách tệp bài làm hiện tại không?", 
      "Thu hồi ngay", 
      () => {
        setFiles([]);
        onNotify("destructive", "Đã thu hồi toàn bộ tệp bài làm.");
      }
    );
  };

  const handleRemoveSingleFile = (e: React.MouseEvent<HTMLButtonElement>, idx: number) => {
    e.stopPropagation();
    const target = files[idx];
    if (!target) return;
    
    openConfirmDialog(
      "Thu hồi tệp tin", 
      `Bạn có muốn loại bỏ tệp "${target.name}" khỏi danh sách nộp bài không?`, 
      "Đồng ý", 
      () => {
        setFiles((prev) => prev.filter((_, index) => index !== idx));
        onNotify("destructive", `Đã thu hồi tệp ${target.name}.`);
      }
    );
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
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", damping: 20, stiffness: 100 }}
        className="rounded-2xl p-6 md:p-8 lg:p-9 relative overflow-hidden text-white brand-gradient shadow-[0_12px_30px_rgba(30,64,175,0.28)]"
      >
        <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute right-8 top-1/2 -translate-y-1/2 opacity-[0.08] pointer-events-none hidden md:block">
          <div className="relative w-44 h-44">
            <FileCode2 className="absolute inset-0 w-44 h-44" />
            <Upload className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14" />
          </div>
        </div>
        <div className="relative">
          <h1 className="text-2xl md:text-4xl font-black tracking-tight uppercase">DSA <span className="text-white/80">AUTOGRADER</span></h1>
          <p className="text-sm md:text-base text-blue-100 mt-2 max-w-xl font-medium">
            Hệ thống chấm bài tự động. Vui lòng điền thông tin và tải lên mã nguồn Python.
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
            ].map((metric, i) => (
              <motion.div
                key={metric.k}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + i * 0.1 }}
                className="rounded-lg bg-white/10 border border-white/20 px-3 py-2"
              >
                <p className="text-[11px] text-blue-100">{metric.k}</p>
                <p className="text-lg font-semibold leading-tight mt-1">{metric.v}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </motion.div>

      <motion.div 
        initial="hidden"
        animate="show"
        variants={{
          hidden: { opacity: 0 },
          show: {
            opacity: 1,
            transition: { duration: 0.2, ease: "easeOut" }
          }
        }}
        className="grid grid-cols-12 gap-5 lg:gap-6 items-stretch"
      >
        {/* Left – Form */}
        <div className="col-span-12 lg:col-span-6 space-y-5">
          <motion.div 
            variants={{ hidden: { opacity: 0, x: -20 }, show: { opacity: 1, x: 0 } }}
            className="card-elevated p-6 lg:p-7 min-h-[300px]"
          >
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
                  className="input transition-all focus:scale-[1.01]"
                />
              </div>
              <div>
                <label className="label">Họ và tên</label>
                <input
                  type="text"
                  value={studentInfo.name}
                  onChange={(e) => setStudentInfo({ ...studentInfo, name: e.target.value })}
                  placeholder="VD: Nguyễn Văn A"
                  className="input transition-all focus:scale-[1.01]"
                />
              </div>
              <div>
              <label className="label text-blue-600 font-bold">Chọn mã bài tập</label>
              <select
                value={(studentInfo as any).assignmentCode || ""}
                onChange={(e) => setStudentInfo({ ...studentInfo, ["assignmentCode" as any]: e.target.value })}
                className="input appearance-none bg-white border-blue-200 focus:ring-blue-600 cursor-pointer transition-all focus:scale-[1.01]"
              >
                <option value="">-- Click để chọn mã bài tập --</option>
                {assignmentCodes.map((code) => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
            </div>
            </div>
          </motion.div>

          <motion.div 
            variants={{ hidden: { opacity: 0, x: -20 }, show: { opacity: 1, x: 0 } }}
            className="card p-5 lg:p-6 min-h-[210px] bg-slate-50/50"
          >
            <h2 className="label-sm mb-4 flex justify-between items-center text-blue-800">
              <span>Yêu cầu & Tiêu chí chấm điểm</span>
              {isLoadingDetail && <span className="animate-pulse text-[10px]">Đang tải...</span>}
            </h2>
            
            <AnimatePresence mode="wait">
              {selectedAssignmentDetail ? (
                <motion.div 
                  key="detail"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-4 overflow-hidden"
                >
                  <div className="bg-white p-3 rounded-lg border border-blue-100">
                    <p className="text-xs font-bold text-blue-600 mb-1 uppercase tracking-wider">Tên bài tập</p>
                    <p className="text-sm font-semibold text-gray-800">{selectedAssignmentDetail.title}</p>
                  </div>

                  <div className="bg-white p-3 rounded-lg border border-gray-100">
                    <p className="text-xs font-bold text-gray-500 mb-1 uppercase tracking-wider">Mô tả bài toán</p>
                    <p className="text-[13px] text-gray-600 leading-relaxed whitespace-pre-wrap">
                      {selectedAssignmentDetail.description || "Không có mô tả chi tiết."}
                    </p>
                  </div>

                  <div className="bg-white p-3 rounded-lg border border-emerald-100 shadow-sm">
                    <p className="text-xs font-bold text-emerald-600 mb-2 uppercase tracking-wider">Hệ thống tiêu chí (Rubric)</p>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto thin-scroll pr-1">
                      {selectedAssignmentDetail.criteria && selectedAssignmentDetail.criteria.length > 0 ? (
                        selectedAssignmentDetail.criteria
                          .filter((c: any) => {
                            const name = String(c.name || "").trim();
                            const isJunk = !name || name === "{" || name === "}" || name === "[" || name === "]" || name === ":" || name === ",";
                            return !isJunk && !name.includes('"tieu_chi"') && !name.includes("tieu_chi:");
                          })
                          .map((c: any, index: number) => (
                          <motion.div 
                            key={index} 
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="flex justify-between items-start gap-3 p-2 bg-emerald-50/30 rounded border border-emerald-50"
                          >
                            <span className="text-[13px] text-gray-700 leading-tight">
                              {c.name}
                            </span>
                            <span className="text-[11px] font-bold text-emerald-700 bg-emerald-100/50 px-1.5 py-0.5 rounded shrink-0">
                              {c.max_score}đ
                            </span>
                          </motion.div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-400 italic">Dựa vào phân tích logic & thuật toán DSA tổng quát.</p>
                      )}
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div 
                  key="placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="h-40 flex flex-col items-center justify-center text-center p-4 border-2 border-dashed border-slate-200 rounded-xl bg-white"
                >
                  <ClipboardList className="w-8 h-8 text-slate-300 mb-2" />
                  <p className="text-xs text-slate-400">Vui lòng chọn Mã bài tập để xem chi tiết tiêu chí chấm điểm từ hệ thống.</p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Right – Upload */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-5">
          <motion.div
            variants={{ hidden: { opacity: 0, scale: 0.98 }, show: { opacity: 1, scale: 1 } }}
            {...(() => {
              const { onAnimationStart, onDragStart, onDragEnd, onDrag, ...props } = getRootProps();
              return props;
            })()}
            className="flex-1 card border-dashed border-2 bg-white flex flex-col items-center justify-center p-8 md:p-12 lg:p-14 min-h-[360px] lg:min-h-[430px] cursor-pointer group hover:border-blue-300 hover:bg-blue-50/30 transition-all"
          >
            <input {...getInputProps()} />
            <motion.div 
              whileHover={{ scale: 1.1, rotate: 5 }}
              className="w-14 h-14 bg-gray-50 border border-gray-200 rounded-xl flex items-center justify-center mb-6 group-hover:bg-blue-600 group-hover:border-blue-600 transition-all shadow-sm"
            >
              <Upload className="w-6 h-6 text-gray-400 group-hover:text-white transition-colors" />
            </motion.div>
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

            <AnimatePresence>
              {files.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="mt-8 w-full max-w-md"
                >
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
                      <motion.div
                        key={file.name + i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ delay: i * 0.05 }}
                        className="bg-white border border-gray-100 rounded-lg px-4 py-3 flex items-center justify-between hover:border-blue-100 hover:shadow-sm transition-all"
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
                          className="text-gray-300 hover:text-red-500 p-0.5 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="sticky bottom-2 pt-2 bg-gradient-to-t from-white via-white/90 to-transparent"
          >
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleValidate}
              disabled={isSubmitting || files.length === 0}
              className="btn-primary w-full h-12 lg:h-14 text-[15px] shadow-lg shadow-blue-200"
            >
              {isSubmitting ? "Đang chuẩn bị chấm điểm..." : "Nộp bài và chấm điểm"}
            </motion.button>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
};
