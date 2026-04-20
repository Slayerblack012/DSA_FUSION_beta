"use client";

import React from "react";
import {
  Code2,
  ChevronDown,
  BadgeCheck,
  ShieldCheck,
  Terminal,
  Copy,
} from "lucide-react";
import toast from "react-hot-toast";
import type { FileEvaluation, ScoreProof } from "@/types";
import { parseAiAdvice, getScorePercent, getCriterionTone } from "@/hooks/useAiAdvice";

interface FileEvaluationCardProps {
  file: FileEvaluation;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

export const FileEvaluationCard = ({
  file,
  isExpanded,
  onToggleExpand,
}: FileEvaluationCardProps) => {

  const structuredFeedback = file.feedbacks.find((fb) =>
    hasStructuredMarkers(fb.message || "")
  );
  const adviceText = (() => {
    const rawAdvice = (file.aiAdvice || "").trim();
    const fallbackAdvice = (
      structuredFeedback?.message ||
      file.feedbacks?.[0]?.message ||
      ""
    ).trim();

    if (fallbackAdvice && hasStructuredMarkers(fallbackAdvice)) return fallbackAdvice;
    if (rawAdvice && !isGenericAdviceText(rawAdvice)) return rawAdvice;
    if (fallbackAdvice) return fallbackAdvice;
    return rawAdvice;
  })();

  const scoreProof = file.scoreProof;
  const parsedAdvice = parseAiAdvice(adviceText, scoreProof);
  const detailFeedbacks = file.feedbacks.filter(
    (fb) => !hasStructuredMarkers(fb.message || "")
  );
  const visibleCriteria = parsedAdvice.criteriaScores;
  const matchedExercise =
    scoreProof?.rubricAdjustment?.matchedExercise ||
    (scoreProof as any)?.rubric_adjustment?.matched_exercise;

  return (
    <div className="card-elevated overflow-hidden">
      <div
        onClick={onToggleExpand}
        className="px-6 py-5 flex items-center justify-between cursor-pointer hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
              isExpanded ? "bg-blue-600 text-white" : "bg-gray-50 text-gray-400"
            }`}
          >
            <Code2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h4 className="text-[15px] font-semibold text-gray-900">{file.fileName}</h4>
              <span
                className={`badge ${file.score >= 5 ? "badge-success" : "badge-error"}`}
              >
                {file.score >= 5 ? "Đạt" : "Chưa đạt"}
              </span>
            </div>
            <p className="text-[12px] text-gray-400 mt-0.5">
              Thời gian: {(file.timeMs / 1000).toFixed(3)}s
            </p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <span className="text-3xl font-bold text-gray-900 tabular-nums">
            {file.score.toFixed(1)}
          </span>
          <div
            className={`w-8 h-8 rounded-md flex items-center justify-center transition-colors ${
              isExpanded ? "bg-blue-600 text-white" : "bg-gray-50 text-gray-400"
            }`}
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform duration-300 ease-out ${
                isExpanded ? "rotate-180" : "rotate-0"
              }`}
            />
          </div>
        </div>
      </div>

      <div
        className={`grid border-t border-gray-100 transition-[grid-template-rows,opacity] duration-300 ease-out ${
          isExpanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          <div className="p-6 space-y-8">
            {/* Advice Section - Chỉ giữ lại bảng tiêu chí và giãn rộng 100% */}
            {adviceText && (
              <div className="space-y-4">
                <div className="rounded-lg border border-blue-100 bg-white p-5 space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="section-title flex items-center gap-2">
                      <BadgeCheck className="w-3.5 h-3.5 text-blue-600" /> Tiêu chí chấm điểm
                    </p>
                    <span className="text-[12px] text-gray-500">
                      {parsedAdvice.criteriaScores.length} tiêu chí
                    </span>
                  </div>
                  {(matchedExercise as any)?.assignmentCode || (matchedExercise as any)?.assignment_code ? (
                    <p className="text-[12px] text-slate-600">
                      Đang dùng rubric từ DB:{" "}
                      <span className="font-semibold">
                        {(matchedExercise as any).assignmentCode || (matchedExercise as any).assignment_code}
                      </span>
                      {(matchedExercise as any).title ? ` - ${(matchedExercise as any).title}` : ""}
                    </p>
                  ) : null}

                  {visibleCriteria.length > 0 ? (
                    <div className="grid grid-cols-1 gap-2">
                      {visibleCriteria
                        .filter((criterion) => {
                          const label = String(criterion.sourceText || criterion.criterion || "").trim();
                          // Extra hardening for post-submission results
                          const isJunk = !label || label === "{" || label === "}" || label === "[" || label === "]" || label === ":" || label === ",";
                          return !isJunk && !label.includes('"tieu_chi"') && !label.includes("tieu_chi:");
                        })
                        .map((criterion, cIdx) => {
                        const scorePercent = getScorePercent(criterion.earned, criterion.total);
                        const tone = getCriterionTone(scorePercent);
                        const criterionLabel = (criterion.sourceText || criterion.criterion || "").replace(/^["']|["']$/g, "").trim();
                        return (
                          <div key={cIdx} className={`rounded-lg border p-3 ${tone.cardClass}`}>
                            <div className="flex items-start justify-between gap-3">
                              <div className="space-y-1">
                                <p className="text-[13px] font-medium text-gray-800 leading-relaxed whitespace-pre-wrap">
                                  {criterionLabel}
                                </p>
                              </div>
                              <span className={`text-[13px] font-semibold tabular-nums shrink-0 ${tone.textClass}`}>
                                {criterion.earned.toFixed(2)}/{criterion.total.toFixed(2)}
                              </span>
                            </div>
                            <div className="mt-2 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                              <div className={`h-full rounded-full ${tone.barClass}`} style={{ width: `${scorePercent}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-[13px] text-gray-500">Chưa có tiêu chí để hiển thị.</p>
                  )}
                </div>
              </div>
            )}

            {/* Bằng chứng điểm số */}
            {scoreProof && (
              <div className="mb-6 rounded-lg border border-emerald-100 bg-emerald-50/50 p-5">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <p className="section-title flex items-center gap-2 text-emerald-700">
                    <ShieldCheck className="w-3.5 h-3.5" /> Nguyên nhân điểm số và bằng chứng
                  </p>
                </div>
                {/* Giữ nguyên hàm renderScoreProof bên dưới */}
                {renderScoreProof(scoreProof, file.score)}
              </div>
            )}

            {/* Gợi ý cải thiện */}
            <div>
              <p className="section-title mb-4">Gợi ý cải thiện mã nguồn</p>
              {renderImprovements(parsedAdvice, detailFeedbacks, adviceText)}
            </div>

            {/* Bài giải tham khảo */}
            {file.optimizedCode && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <p className="section-title flex items-center gap-2">
                    <Terminal className="w-3.5 h-3.5" /> Bài giải tham khảo
                  </p>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(file.optimizedCode!);
                      toast.success("Đã sao chép mã nguồn");
                    }}
                    className="btn-secondary text-[12px] h-8 px-3"
                  >
                    <Copy className="w-3.5 h-3.5" /> Sao chép
                  </button>
                </div>
                <div className="rounded-lg overflow-hidden border border-gray-200">
                  <div className="p-5 bg-gray-900 overflow-x-auto max-h-[400px]">
                    <pre className="text-[13px] font-mono text-gray-300 leading-relaxed">
                      <code>{file.optimizedCode}</code>
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ---- Inline helpers (kept inside file to avoid circular deps) ----

function isGenericAdviceText(value: string) {
  const normalized = value.toLowerCase().replace(/\s+/g, " ").trim();
  if (!normalized) return true;
  return [
    "tiếng việt",
    "code đã tối ưu",
    "không có đánh giá",
    "không có phân tích",
    "không có nhận xét",
    "n/a",
  ].some(
    (fragment) =>
      normalized === fragment || normalized.includes(fragment)
  );
}

function hasStructuredMarkers(value: string) {
  return /\[ANALYSIS\]|\[HINT\]|\[ISSUES_FOUND\]|Chấm theo tiêu chí|Phân tích kỹ thuật|Gợi ý cải thiện|Điểm theo tiêu chí|Bảng điểm chi tiết/i.test(
    value || ""
  );
}

function renderScoreProof(scoreProof: ScoreProof, fileScore: number) {
  const proofItems = (
    scoreProof.rubricAdjustment?.criteriaResults ||
    (scoreProof as unknown as { rubric_adjustment?: { criteria_results?: Array<Record<string, unknown>> } })
      ?.rubric_adjustment?.criteria_results ||
    []
  )
    .map((item) => {
      const rawLabel = String(
        (item as { sourceText?: string; source_text?: string; name?: string })?.sourceText ||
          (item as { sourceText?: string; source_text?: string; name?: string })?.source_text ||
          item?.name ||
          ""
      ).trim();

      // STRICT FILTER: Skip JSON noise
      if (!rawLabel || rawLabel === "{" || rawLabel === "}" || rawLabel === "[" || rawLabel === "]" || rawLabel.includes('"tieu_chi"')) {
        return null;
      }

      const criterion = formatCriterionLabel(rawLabel);
      const earned = Number(item?.earned ?? 0);
      const total = Number(item?.max ?? 0);
      
      if (!criterion || Number.isNaN(earned) || Number.isNaN(total) || total <= 0)
        return null;
        
      return {
        criterion: criterion.replace(/^["']|["']$/g, "").trim(),
        earned,
        total,
        feedback: String(item?.feedback || "").trim(),
        evidence: String(item?.evidence || "").trim(),
      };
    })
    .filter(
      (item): item is { criterion: string; earned: number; total: number; feedback: string; evidence: string } =>
        item !== null
    );

  if (proofItems.length === 0) {
    return (
      <div className="p-4 rounded-xl bg-white border border-emerald-100 text-[13px] text-gray-500 text-center italic">
        Bằng chứng chi tiết sẽ được tự động cập nhật từ kết quả phân tích AI và Rubric.
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {proofItems.map((item, idx) => (
        <div key={idx} className="bg-white rounded-xl p-5 border border-emerald-100 shadow-sm space-y-4">
          <div className="flex justify-between items-start gap-4">
            <h4 className="text-[14px] font-bold text-slate-800 flex items-start gap-2 leading-snug">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
              {item.criterion}
            </h4>
            <span className="text-[12px] font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full tabular-nums whitespace-nowrap">
              {item.earned.toFixed(1)} / {item.total.toFixed(0)}
            </span>
          </div>
          
          <div className="grid gap-3 border-l-2 border-emerald-100/50 pl-4 ml-0.5">
            {item.feedback && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600/70 block">Nguyên nhân (Reason)</span>
                <p className="text-[13px] text-slate-600 leading-relaxed font-medium">
                  {item.feedback}
                </p>
              </div>
            )}
            {item.evidence && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600/70 block">Bằng chứng (Evidence)</span>
                <p className="text-[13px] text-slate-500 italic bg-slate-50 p-2.5 rounded-lg border border-slate-100 font-mono break-all">
                  {item.evidence}
                </p>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function renderImprovements(
  parsedAdvice: ReturnType<typeof parseAiAdvice>,
  detailFeedbacks: { hint?: string; message?: string }[],
  adviceText: string
) {
  const improvementItems: string[] = [];
  if (adviceText) {
    let inTargetSection = false;
    const lines = adviceText.split("\n");
    for (const line of lines) {
      if (/^###\s*(lỗi và vấn đề cần sửa|gợi ý cải thiện|nhận xét chuyên môn)/i.test(line.trim())) {
        inTargetSection = true; continue;
      } else if (/^###|^chi tiết chấm điểm/i.test(line.trim())) {
        inTargetSection = false; continue;
      }
      if (inTargetSection) {
        const cleaned = line.replace(/^[-*•]\s*/, "").trim();
        if (cleaned && !/^[0-9.,]+\s*\/\s*[0-9.,]+đ?$/i.test(cleaned)) improvementItems.push(cleaned);
      }
    }
  }
  parsedAdvice.improvements.forEach((imp) => improvementItems.push(imp));
  detailFeedbacks.forEach((fb) => {
    if (fb.hint && !fb.hint.toLowerCase().includes("điểm bên dưới được chuẩn hóa")) improvementItems.push(fb.hint.trim());
  });

  let finalItems = improvementItems
    .map(item => item.replace(/^Khắc phục:\s*/, "").trim())
    .filter(item => item.length > 10)
    .filter((v, i, a) => a.findIndex((t) => t.toLowerCase() === v.toLowerCase()) === i)
    .slice(0, 4);

  if (finalItems.length === 0) {
    return (
      <div className="p-6 rounded-2xl bg-success/5 border border-success/10 text-center">
         <p className="text-sm text-success font-medium italic">&quot;Giải thuật của em đã rất tối ưu. Hãy tiếp tục duy trì phong cách code sạch và hiệu quả này!&quot;</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {finalItems.map((item, idx) => (
        <div key={idx} className="card-glass border-white/5 p-5 flex gap-4 hover:border-primary/30 transition-all group">
          <div className="h-8 w-8 rounded-full bg-white/5 flex items-center justify-center text-xs font-bold text-primary shrink-0 group-hover:bg-primary group-hover:text-white transition-all">
            0{idx + 1}
          </div>
          <p className="text-[13px] text-text-main/80 leading-relaxed font-medium">
            {item}
          </p>
        </div>
      ))}
    </div>
  );
}

function formatCriterionLabel(value: string) {
  const normalized = collapseWhitespace(value);
  if (!normalized) return "Tiêu chí chưa có mô tả rõ ràng";

  const extracted = extractCriterionParts(normalized);
  if (extracted.length > 0) {
    return extracted.join("\n");
  }

  return normalized
    .replace(/^\{\s*"?tieu_chi"?\s*:\s*\[/i, "")
    .replace(/\]\s*\}?$/i, "")
    .replace(/["'`]/g, "")
    .replace(/\s*[,;]\s*/g, " • ")
    .trim();
}

function extractCriterionParts(value: string) {
  const cleaned = value.trim();
  if (!cleaned) return [];

  const tryParse = (text: string) => {
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return null;
    }
  };

  const parsed = cleaned.startsWith("{") || cleaned.startsWith("[") ? tryParse(cleaned) : null;

  if (Array.isArray(parsed)) {
    return parsed.map((item) => cleanCriterionPart(String(item))).filter(Boolean);
  }

  if (parsed && typeof parsed === "object") {
    const objectValue = parsed as Record<string, unknown>;
    const directArray =
      objectValue.tieu_chi ?? objectValue.criteria ?? objectValue.items ?? objectValue.parts;

    if (Array.isArray(directArray)) {
      return directArray.map((item) => cleanCriterionPart(String(item))).filter(Boolean);
    }

    if (typeof directArray === "string") {
      return [cleanCriterionPart(directArray)].filter(Boolean);
    }

    for (const key of ["tieu_chi", "criteria", "title", "name", "criterion", "label"]) {
      const raw = objectValue[key];
      if (typeof raw === "string") {
        return [cleanCriterionPart(raw)].filter(Boolean);
      }
    }
  }

  if (/^\{\s*"?tieu_chi"?\s*:\s*\[/i.test(cleaned)) {
    const inner = cleaned
      .replace(/^\{\s*"?tieu_chi"?\s*:\s*\[/i, "")
      .replace(/\]\s*\}?$/i, "");
    const splitParts = inner
      .split(/\s*[,;•]\s*/)
      .map((item) => cleanCriterionPart(item))
      .filter(Boolean);
    if (splitParts.length > 0) return splitParts;
  }

  return [];
}

function cleanCriterionPart(value: string) {
  return collapseWhitespace(value)
    .replace(/^[-*•]+\s*/, "")
    .replace(/^\"|\"$/g, "")
    .replace(/^\'|\'$/g, "")
    .trim();
}

function collapseWhitespace(value: string) {
  return value.replace(/\r/g, " ").replace(/\s+/g, " ").trim();
}

function toStudentAdvice(value: string) {
  const cleaned = stripAdviceHeading(
    collapseWhitespace(value)
  )
    .replace(/^Khắc phục:\s*/i, "")
    .trim();

  if (!cleaned) return "";

  if (isHeadingOnlyAdvice(cleaned)) return "";

  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function stripAdviceHeading(value: string) {
  return value
    .replace(/^#{1,6}\s*/g, "")
    .replace(/^[-*]\s*/g, "")
    .replace(/^\[?(?:analysis|hint|issues_found|phân tích kỹ thuật|điểm theo tiêu chí|bảng điểm chi tiết)\]?[:\s-]*/i, "")
    .trim();
}

function isHeadingOnlyAdvice(value: string) {
  const normalized = collapseWhitespace(value).toLowerCase();
  return [
    "phân tích kỹ thuật",
    "điểm theo tiêu chí",
    "bảng điểm chi tiết",
    "phân tích nhanh",
    "gợi ý ngắn",
    "lời khuyên cải thiện mã nguồn",
  ].includes(normalized);
}
