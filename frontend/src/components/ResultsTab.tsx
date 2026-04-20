"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Search,
  ChevronDown,
  Code2,
  MessageCircle,
  Clock,
  ShieldCheck,
  Award,
  Zap,
  Layers,
  GraduationCap,
} from "lucide-react";
import type {
  ResultRecord,
  ResultFileFilter,
  ResultFileSort,
  FileEvaluation,
  ScoreProof,
} from "@/types";
import { parseAiAdvice, getScorePercent, getCriterionTone } from "@/hooks/useAiAdvice";
import { FileEvaluationCard } from "./FileEvaluationCard";

interface ResultsTabProps {
  latest: ResultRecord | null;
  studentInfo: { id: string; name: string };
  onBackToSubmit: () => void;
}

export const ResultsTab = ({ latest, studentInfo, onBackToSubmit }: ResultsTabProps) => {
  const [expandedFileId, setExpandedFileId] = useState<string | null>(null);
  const [resultSearchTerm, setResultSearchTerm] = useState("");
  const [resultFileFilter, setResultFileFilter] = useState<ResultFileFilter>("all");
  const [resultFileSort, setResultFileSort] = useState<ResultFileSort>("score-asc");

  if (!latest) {
    return (
      <div className="py-32 flex flex-col items-center justify-center text-center">
        <p className="text-base font-semibold text-gray-500">Chưa có kết quả nào</p>
        <p className="text-sm text-gray-400 mt-1">
          Nộp bài tập đầu tiên để xem báo cáo tại đây.
        </p>
        <button
          onClick={onBackToSubmit}
          className="btn-primary mt-6 h-10 px-5 text-sm"
        >
          Bắt đầu nộp bài
        </button>
      </div>
    );
  }

  const totalTests =
    latest.fileEvaluations.reduce((acc, f) => acc + f.feedbacks.length, 0) ?? 0;
  const passedTests =
    latest.fileEvaluations.reduce(
      (acc, f) => acc + f.feedbacks.filter((fb) => fb.status === "AC").length,
      0
    ) ?? 0;
  const passedFiles = latest.fileEvaluations.filter((f) => f.score >= 5).length ?? 0;
  const avgFileScore = latest.fileEvaluations.length
    ? latest.fileEvaluations.reduce((acc, f) => acc + f.score, 0) /
      latest.fileEvaluations.length
    : 0;
  const passRate = totalTests ? Math.round((passedTests / totalTests) * 100) : 0;

  const normalizedSearchTerm = resultSearchTerm.trim().toLowerCase();
  const filteredFileEvaluations = [...latest.fileEvaluations]
    .filter((file) => {
      if (resultFileFilter === "passed" && file.score < 5) return false;
      if (resultFileFilter === "failed" && file.score >= 5) return false;
      if (!normalizedSearchTerm) return true;
      return file.fileName.toLowerCase().includes(normalizedSearchTerm);
    })
    .sort((a, b) => {
      if (resultFileSort === "score-asc") return a.score - b.score;
      if (resultFileSort === "score-desc") return b.score - a.score;
      if (resultFileSort === "name-asc")
        return a.fileName.localeCompare(b.fileName, "vi");
      return b.timeMs - a.timeMs;
    });

  const failedInFiltered = filteredFileEvaluations.filter((f) => f.score < 5).length;
  const quickFocusFailedActive =
    resultFileFilter === "failed" && resultFileSort === "score-asc";

  const displayStudentName = latest.studentName || studentInfo.name || "—";
  const displayStudentId = latest.studentId || studentInfo.id || "—";

  return (
    <div className="space-y-5 pt-2 md:pt-3 pb-20 motion-perf">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          {
            label: "Tệp đạt",
            value: `${passedFiles}/${latest.fileEvaluations.length}`,
            tone: "text-emerald-700 bg-emerald-50 border-emerald-100",
          },
          {
            label: "Tỷ lệ test đạt",
            value: `${passRate}%`,
            tone: "text-blue-700 bg-blue-50 border-blue-100",
          },
          {
            label: "Điểm trung binh của tất cả bài nộp",
            value: avgFileScore.toFixed(2),
            tone: "text-orange-700 bg-orange-50 border-orange-100",
          },
          {
            label: "Tổng test",
            value: String(totalTests),
            tone: "text-gray-700 bg-gray-50 border-gray-100",
          },
        ].map((kpi) => (
          <motion.div
            key={kpi.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className={`rounded-xl border px-4 py-3 min-h-[74px] ${kpi.tone}`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-wide opacity-80">
              {kpi.label}
            </p>
            <p className="text-xl font-bold mt-1 tabular-nums">{kpi.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Score Header */}
      <div className="grid grid-cols-12 gap-5 items-stretch">
        <motion.div
          className="col-span-12 xl:col-span-9 rounded-xl p-7 bg-blue-600 text-white relative overflow-hidden motion-perf min-h-[200px]"
        >
          <div className="absolute top-4 right-4 opacity-5">
            <GraduationCap className="w-40 h-40" />
          </div>
          <div className="relative space-y-6">
            <div className="flex items-center gap-3">
              <span className="badge bg-white/20 text-white text-[11px] border-none">
                Hoàn tất
              </span>
              <span className="text-white/50 text-[12px] flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> {latest.timestamp}
              </span>
            </div>
            <div>
              <h2 className="text-2xl font-bold">Báo cáo kết quả chấm điểm</h2>
              <p className="text-blue-200 text-sm mt-1">
                Đánh giá tự động và nhận xét chi tiết
              </p>
            </div>
            <div className="flex items-end justify-between pt-6 border-t border-white/15">
              <div>
                <p className="text-[11px] text-white/50 font-medium mb-1">Sinh viên</p>
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-white/20 rounded-full flex items-center justify-center font-semibold text-lg">
                    {displayStudentName.charAt(0) || "?"}
                  </div>
                  <div>
                    <p className="text-lg font-semibold">{displayStudentName}</p>
                    <p className="text-xs text-blue-200/90">MSSV: {displayStudentId}</p>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[11px] text-white/50 font-medium mb-1">Mã phiên</p>
                <p className="font-mono text-sm text-blue-200">{latest.id}</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Score Ring */}
        <motion.div className="col-span-12 xl:col-span-3 card-elevated p-7 flex flex-col items-center justify-center text-center motion-perf min-h-[200px] h-full">
          <p className="section-title mb-4">Điểm trung bình</p>
          <div className="relative w-36 h-36 flex items-center justify-center mb-4">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
              <circle cx="80" cy="80" r="68" stroke="#f3f4f6" strokeWidth="8" fill="transparent" />
              <motion.circle
                cx="80"
                cy="80"
                r="68"
                stroke="#2563eb"
                strokeWidth="8"
                fill="transparent"
                strokeDasharray="427"
                initial={{ strokeDashoffset: 427 }}
                animate={{
                  strokeDashoffset: 427 - latest.totalScore * 42.7,
                }}
                strokeLinecap="round"
                transition={{ duration: 1.2, ease: "easeOut" }}
              />
            </svg>
            <span className="absolute text-4xl font-bold text-gray-900 tabular-nums">
              {latest.totalScore.toFixed(1)}
            </span>
          </div>
          <div
            className={`badge ${
              latest.totalScore >= 8.5
                ? "badge-success"
                : latest.totalScore >= 5
                ? "badge-blue"
                : "badge-error"
            }`}
          >
            {latest.totalScore >= 8.5
              ? "Xuất sắc"
              : latest.totalScore >= 5
              ? "Đạt yêu cầu"
              : "Chưa đạt"}
          </div>
        </motion.div>
      </div>

      {/* File Evaluations */}
      <div className="space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="section-title px-1">Chi tiết từng tệp</p>
            <p className="text-[12px] text-gray-500 mt-1 px-1">
              Đang hiển thị {filteredFileEvaluations.length}/
              {latest.fileEvaluations.length} tệp, còn {failedInFiltered} tệp chưa đạt trong danh
              sách lọc.
            </p>
          </div>
          <div className="flex flex-col md:flex-row flex-wrap items-stretch md:items-center gap-2 w-full xl:w-auto">
            <button
              onClick={() => {
                if (quickFocusFailedActive) {
                  setResultFileFilter("all");
                  setResultFileSort("score-asc");
                  return;
                }
                setResultFileFilter("failed");
                setResultFileSort("score-asc");
                setResultSearchTerm("");
              }}
              className={`h-10 rounded-lg border px-3 text-[13px] font-medium transition-colors whitespace-nowrap shrink-0 ${
                quickFocusFailedActive
                  ? "border-rose-300 bg-rose-50 text-rose-700"
                  : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              {quickFocusFailedActive
                ? "Đang xem file chưa đạt"
                : "1 click: chỉ file chưa đạt"}
            </button>
            <div className="relative shrink-0 w-full md:w-52">
              <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={resultSearchTerm}
                onChange={(e) => setResultSearchTerm(e.target.value)}
                placeholder="Tìm theo tên tệp..."
                className="h-10 w-full rounded-lg border border-gray-200 bg-white pl-9 pr-3 text-[13px] text-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>
            <select
              value={resultFileFilter}
              onChange={(e) => setResultFileFilter(e.target.value as ResultFileFilter)}
              className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200 shrink-0 w-full md:w-auto"
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="failed">Chỉ chưa đạt</option>
              <option value="passed">Chỉ đạt</option>
            </select>
            <select
              value={resultFileSort}
              onChange={(e) => setResultFileSort(e.target.value as ResultFileSort)}
              className="h-10 rounded-lg border border-gray-200 bg-white px-3 text-[13px] text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200 shrink-0 w-full md:w-auto"
            >
              <option value="score-asc">Ưu tiên điểm thấp</option>
              <option value="score-desc">Điểm cao trước</option>
              <option value="name-asc">Tên tệp A-Z</option>
              <option value="time-desc">Thời gian chạy lâu trước</option>
            </select>
          </div>
        </div>

        {filteredFileEvaluations.map((file, i) => (
          <FileEvaluationCard
            key={i}
            file={file}
            isExpanded={expandedFileId === file.fileName}
            onToggleExpand={() =>
              setExpandedFileId(
                expandedFileId === file.fileName ? null : file.fileName
              )
            }
          />
        ))}
      </div>
    </div>
  );
};
