// ============================================================
// Shared TypeScript types for DSA Autograder Frontend
// ============================================================

export interface Feedback {
  testcase: string;
  status: "AC" | "WA" | "TLE" | "RE";
  message: string;
  points: number;
  hint?: string;
}

export interface AgentTraceEntry {
  step?: string;
  status?: string;
  message?: string;
  provider?: string;
  timestamp?: string;
  [key: string]: unknown;
}

export interface ScoreProof {
  mode?: string;
  policy_version?: string;
  formula?: string;
  weights?: Record<string, number>;
  effectiveWeights?: Record<string, number>;
  components?: Record<string, number>;
  rawWeighted?: number;
  finalScore?: number;
  rubricAdjustment?: {
    applied?: boolean;
    before?: number;
    after?: number;
    source?: string;
    criteriaResults?: Array<{
      name?: string;
      criteriaCode?: string;
      earned?: number;
      max?: number;
      feedback?: string;
      evidence?: string;
      sourceText?: string;
    }>;
    matchedExercise?: {
      assignmentCode?: string;
      title?: string;
    };
    matchProof?: {
      score?: number;
      margin?: number;
      lowConfidence?: boolean;
    };
  };
}

export interface FileEvaluation {
  fileName: string;
  score: number;
  feedbacks: Feedback[];
  aiAdvice?: string;
  improvement?: string;
  optimizedCode?: string;
  timeMs: number;
  agentTrace?: AgentTraceEntry[];
  scoreProof?: ScoreProof;
  criteriaScores?: RubricCriterionScore[];
}

export interface RubricCriterionScore {
  criterion: string;
  criteriaCode?: string;
  earned: number;
  total: number;
  sourceText?: string;
  feedback?: string;
  evidence?: string;
}

export interface RubricCriterionScoreView extends RubricCriterionScore {
  scorePercent: number;
}

export interface ParsedAiAdvice {
  analysis: string;
  hint: string;
  issues: string[];
  criteriaScores: RubricCriterionScore[];
  fallbackText: string;
  improvements: string[];
}

export interface ResultRecord {
  id: string;
  studentId: string;
  studentName: string;
  assignmentCode?: string;
  totalScore: number;
  fileEvaluations: FileEvaluation[];
  overallAiSummary?: string;
  timestamp: string;
  totalTimeMs: number;
}

export type AppTab = "submit" | "history" | "settings";

export interface SystemSettings {
  requestTimeoutMs: number;
  autoOpenHistory: boolean;
  enableNotifications: boolean;
  rememberStudent: boolean;
}

export interface ConfirmDialogState {
  open: boolean;
  title: string;
  message: string;
  confirmText: string;
  onConfirm: (() => void) | null;
}

export type ResultFileFilter = "all" | "passed" | "failed";
export type ResultFileSort = "score-asc" | "score-desc" | "name-asc" | "time-desc";

export interface StudentInfo {
  id: string;
  name: string;
  assignmentCode?: string;
}
