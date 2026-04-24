// ============================================================
// Utility hooks for AI advice parsing, score formatting, etc.
// ============================================================

import {
  ParsedAiAdvice,
  RubricCriterionScore,
  ScoreProof,
} from "@/types";

// ---- Score helpers ----

export const getScorePercent = (earned: number, total: number) =>
  total > 0 ? Math.max(0, Math.min(100, (earned / total) * 100)) : 0;

export const getCriterionTone = (scorePercent: number) => {
  if (scorePercent < 50) {
    return {
      cardClass: "border-rose-200 bg-rose-50/80",
      textClass: "text-rose-700",
      barClass: "bg-rose-500",
    };
  }
  if (scorePercent < 80) {
    return {
      cardClass: "border-amber-200 bg-amber-50/80",
      textClass: "text-amber-700",
      barClass: "bg-amber-500",
    };
  }
  return {
    cardClass: "border-emerald-200 bg-emerald-50/80",
    textClass: "text-emerald-700",
    barClass: "bg-emerald-500",
  };
};

export const normalizeCriterionKey = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();

export const toNumber = (value: string) => Number(value.replace(",", "."));

const readString = (value: unknown) =>
  typeof value === "string"
    ? value.trim()
    : value === null || value === undefined
      ? ""
      : String(value).trim();

const readNumber = (value: unknown) => {
  const parsed = typeof value === "string" ? Number(value.replace(",", ".")) : Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

const normalizeCriterionScore = (
  item: RubricCriterionScore | Record<string, unknown>
): RubricCriterionScore | null => {
  const raw = item as Record<string, unknown>;
  const sourceText = readString(raw.sourceText ?? raw.source_text);
  const criterion = readString(raw.criterion ?? raw.name ?? sourceText);
  const earned = readNumber(raw.earned);
  const total = readNumber(raw.total ?? raw.max ?? raw.max_score);

  if (!criterion || total <= 0) return null;

  return {
    criterion,
    criteriaCode: readString(raw.criteriaCode ?? raw.criteria_code) || undefined,
    earned,
    total,
    sourceText: sourceText || undefined,
    feedback: readString(raw.feedback ?? raw.comment) || undefined,
    evidence: readString(raw.evidence ?? raw.source_text) || undefined,
  };
};

export const isGenericAdviceText = (value: string) => {
  const normalized = value.toLowerCase().replace(/\s+/g, " ").trim();
  if (!normalized) return true;
  return [
    "tiếng việt",
    "code đã tối ưu",
    "không có đánh giá",
    "không có phân tích",
    "không có nhận xét",
    "n/a",
  ].some((fragment) => normalized === fragment || normalized.includes(fragment));
};

// ---- Text cleaning ----

export const cleanAdviceText = (text: string) =>
  text
    .replace(/\r/g, "")
    .replace(/\*\*/g, "")
    .replace(/^#{1,6}\s*/gm, "")
    .trim();

export const stripAiMarkers = (text: string) =>
  text
    .replace(
      /\[(TECHNICAL_REVIEW|RUBRIC SCORES|SCORE BREAKDOWN|GỢI Ý CẢI THIỆN|ANALYSIS|HINT|ISSUES_FOUND)\]/gi,
      ""
    )
    .replace(/\b(PHÂN TÍCH CHẤM ĐIỂM|BẢNG ĐIỂM CHI TIẾT|CHẤM THEO TIÊU CHÍ DB|LỜI KHUYÊN CẢI THIỆN)\b/gi, "")
    .replace(/^\[\]$/gm, "")
    .replace(/\s{2,}/g, " ")
    .trim();

export const toAdviceLines = (text: string): string[] => {
  const normalized = stripAiMarkers(text)
    .replace(/\s-\s/g, "\n- ")
    .replace(/\|\s*Evidence\s*:/gi, "\nEvidence: ")
    .replace(/\n{3,}/g, "\n\n");

  return normalized
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => {
      if (!line) return false;
      if (/^(evidence\s*:|->\s*độ phức tạp)/i.test(line)) return false;
      if (/^(tính đúng đắn|chất lượng code|hiệu năng|cấu trúc|tài liệu|bảo mật)\s*:/i.test(line))
        return false;
      if (/^[0-9]+(?:[.,][0-9]+)?\s*\/\s*[0-9]+(?:[.,][0-9]+)?$/i.test(line)) return false;
      return true;
    });
};

// ---- Section parsing ----

const parseSection = (text: string, section: string, nextSections: string[]) => {
  const escaped = section.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const next = nextSections.length
    ? nextSections.map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")
    : "";
  const pattern = next
    ? new RegExp(`\\[${escaped}\\]([\\s\\S]*?)(?=\\[(?:${next})\\]|$)`, "i")
    : new RegExp(`\\[${escaped}\\]([\\s\\S]*?)$`, "i");
  const match = text.match(pattern);
  return match?.[1]?.trim() || "";
};

// ---- AI advice parser ----

export const parseAiAdvice = (
  rawAdvice?: string,
  scoreProof?: ScoreProof,
  directCriteriaScores?: Array<RubricCriterionScore | Record<string, unknown>>
): ParsedAiAdvice => {
  const text = rawAdvice ? cleanAdviceText(rawAdvice) : "";

  const analysis = parseSection(text, "ANALYSIS", ["HINT", "ISSUES_FOUND"])
    .replace(/^PHÂN TÍCH CHẤM ĐIỂM\s*/i, "")
    .trim();

  const hint = parseSection(text, "HINT", ["ISSUES_FOUND"])
    .replace(/^GỢI Ý CẢI THIỆN\s*/i, "")
    .trim();

  const issuesBlock = parseSection(text, "ISSUES_FOUND", []);
  const issues = issuesBlock
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /^-\s*/.test(line))
    .map((line) => line.replace(/^-\s*/, "").trim());

  const rawCriteriaScores = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /^-\s*.+:\s*[0-9]+(?:[.,][0-9]+)?\s*\/\s*[0-9]+(?:[.,][0-9]+)?/i.test(line))
    .map((line): RubricCriterionScore | null => {
      const match = line.match(
        /^-\s*(.+?):\s*([0-9]+(?:[.,][0-9]+)?)\s*\/\s*([0-9]+(?:[.,][0-9]+)?)/i
      );
      if (!match) return null;
      const [, criterion, earnedRaw, totalRaw] = match;
      const feedback = line
        .split("|")
        .slice(1)
        .map((part) => part.replace(/^Evidence\s*:/i, "").trim())
        .filter(Boolean)
        .join(" ");
      return {
        criterion: criterion.trim(),
        earned: toNumber(earnedRaw),
        total: toNumber(totalRaw),
        feedback: feedback || undefined,
      };
    })
    .filter(
      (item): item is RubricCriterionScore => item !== null
    );

  const directCriteria = (directCriteriaScores || [])
    .map((item) => normalizeCriterionScore(item))
    .filter((item): item is RubricCriterionScore => item !== null);

  const proofCriteriaRaw =
    scoreProof?.rubricAdjustment?.criteriaResults ||
    (scoreProof as unknown as { rubric_adjustment?: { criteria_results?: Array<Record<string, unknown>> } })
      ?.rubric_adjustment?.criteria_results ||
    [];
  const proofCriteria = proofCriteriaRaw
    .map((item) => normalizeCriterionScore(item as Record<string, unknown>))
    .filter((item): item is RubricCriterionScore => item !== null);

  const criteriaScores =
    directCriteria.length > 0
      ? directCriteria
      : proofCriteria.length > 0
        ? proofCriteria
      : (() => {
          const mergedCriteriaMap = new Map<string, RubricCriterionScore>();
          rawCriteriaScores.forEach((item) => {
            const key = normalizeCriterionKey(item.criterion);
            const existing = mergedCriteriaMap.get(key);
            if (!existing) {
              mergedCriteriaMap.set(key, { ...item });
              return;
            }
            mergedCriteriaMap.set(key, {
              criterion: existing.criterion,
              earned: existing.earned + item.earned,
              total: existing.total + item.total,
            });
          });

          return Array.from(mergedCriteriaMap.values()).sort((a, b) => {
            const percentA = getScorePercent(a.earned, a.total);
            const percentB = getScorePercent(b.earned, b.total);
            if (percentA !== percentB) return percentA - percentB;
            return a.criterion.localeCompare(b.criterion, "vi");
          });
        })();

  const consumedFragments = [
    "[ANALYSIS]",
    "[HINT]",
    "[ISSUES_FOUND]",
    "[TECHNICAL REVIEW]",
    "[RUBRIC SCORES]",
    "[SCORE BREAKDOWN]",
    "[GỢI Ý CẢI THIỆN]",
    "Chấm theo tiêu chí từ cơ sở dữ liệu",
    "PHÂN TÍCH CHẤM ĐIỂM",
    "GỢI Ý CẢI THIỆN",
    "BẢNG ĐIỂM CHI TIẾT",
  ];
  let fallbackText = text;
  consumedFragments.forEach((fragment) => {
    fallbackText = fallbackText.replace(
      new RegExp(fragment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi"),
      ""
    );
  });
  fallbackText = fallbackText
    .split("\n")
    .filter((line) => {
      const trimmed = line.trim();
      if (!trimmed) return false;
      if (/^-\s*Lỗi\s*\d+:/i.test(trimmed)) return false;
      if (/^-\s*.+:\s*[0-9]+(?:[.,][0-9]+)?\s*\/\s*[0-9]+(?:[.,][0-9]+)?/i.test(trimmed))
        return false;
      return true;
    })
    .join("\n")
    .trim();

  const improvements = [
    ...toAdviceLines(hint),
    ...toAdviceLines(fallbackText).filter((line) =>
      /^(em\s+)?(có thể|nên|hãy|cần|ưu tiên|tránh|thêm|tách|đổi|tối ưu|kiểm tra|xử lý|bổ sung|viết|đặt|giảm|sửa)/i.test(line)
    ),
  ]
    .map((line) => line.replace(/^-\s*/, "").trim())
    .filter(Boolean)
    .filter(
      (line, idx, arr) =>
        arr.findIndex((x) => x.toLowerCase() === line.toLowerCase()) === idx
    )
    .slice(0, 8);

  return {
    analysis: stripAiMarkers(analysis),
    hint: stripAiMarkers(hint),
    issues,
    criteriaScores,
    fallbackText: stripAiMarkers(fallbackText),
    improvements,
  };
};

export const normalizeFeedbackTitle = (title: string) => {
  const normalized = (title || "").toLowerCase();
  if (normalized.includes("phân tích cấu trúc") || normalized.includes("ast")) {
    return "Lời khuyên cải thiện";
  }
  return title || "Lời khuyên";
};

export const formatTraceLabel = (value?: string) => {
  const normalized = (value || "").toLowerCase();
  if (normalized.includes("observe") || normalized.includes("start")) return "Observe";
  if (normalized.includes("repair") || normalized.includes("heal")) return "Repair";
  if (normalized.includes("verify") || normalized.includes("validate")) return "Verify";
  if (normalized.includes("fallback")) return "Fallback";
  if (!value) return "Step";
  return value;
};

export const getTraceTone = (value?: string) => {
  const normalized = (value || "").toLowerCase();
  if (normalized.includes("error") || normalized.includes("fail")) {
    return {
      dotClass: "bg-rose-500",
      labelClass: "text-rose-700",
      cardClass: "border-rose-200 bg-rose-50/70",
    };
  }
  if (normalized.includes("fallback") || normalized.includes("warn")) {
    return {
      dotClass: "bg-amber-500",
      labelClass: "text-amber-700",
      cardClass: "border-amber-200 bg-amber-50/70",
    };
  }
  if (
    normalized.includes("ok") ||
    normalized.includes("done") ||
    normalized.includes("success") ||
    normalized.includes("verified")
  ) {
    return {
      dotClass: "bg-emerald-500",
      labelClass: "text-emerald-700",
      cardClass: "border-emerald-200 bg-emerald-50/70",
    };
  }
  return {
    dotClass: "bg-blue-500",
    labelClass: "text-blue-700",
    cardClass: "border-blue-200 bg-blue-50/70",
  };
};
