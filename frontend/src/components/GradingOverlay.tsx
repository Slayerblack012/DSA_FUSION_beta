"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Scan, Terminal } from "lucide-react";

const GRADING_STEPS = [
  "Khởi tạo phiên xử lý...",
  "Phân tích bài nộp...",
  "Chạy bộ kiểm thử tự động...",
  "Đối soát dữ liệu đầu ra...",
  "Tổng hợp báo cáo kết quả...",
];

export const GradingOverlay = () => {
  const [progress, setProgress] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    const pTimer = setInterval(() => setProgress((p) => Math.min(p + 1, 99)), 100);
    const sTimer = setInterval(
      () => setStep((s) => (s + 1) % GRADING_STEPS.length),
      1200
    );
    return () => {
      clearInterval(pTimer);
      clearInterval(sTimer);
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[200] overlay-backdrop flex flex-col items-center justify-center motion-perf"
    >
      {/* Scanner */}
      <div className="relative mb-12">
        <div className="relative flex h-20 w-20 items-center justify-center overflow-hidden rounded-[1.5rem] border border-white/70 bg-white/90 shadow-[0_24px_45px_rgba(15,23,42,0.12)]">
          <Scan className="w-8 h-8 text-blue-600" />
          <motion.div
            animate={{ top: ["0%", "100%", "0%"] }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            className="absolute inset-x-0 h-px bg-blue-500 z-10"
          />
        </div>
      </div>

      {/* Progress */}
      <div className="text-center space-y-6 w-full max-w-sm px-6">
        <div className="space-y-3">
          <p className="text-4xl font-bold text-white tabular-nums drop-shadow-sm">{progress}%</p>
          <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              animate={{ width: `${progress}%` }}
              transition={{ type: "spring", stiffness: 150, damping: 24, mass: 0.8 }}
              className="h-full rounded-full bg-gradient-to-r from-blue-500 via-sky-500 to-cyan-400"
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ y: 4, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -4, opacity: 0 }}
            className="flex items-center justify-center gap-2 text-sm font-medium text-slate-200"
          >
            <Terminal className="w-3.5 h-3.5 text-blue-600" />
            {GRADING_STEPS[step]}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* Status dots */}
      <div className="absolute bottom-12 right-12 hidden lg:block text-left opacity-40">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-200">
          Trạng thái hệ thống
        </p>
        <div className="space-y-1 font-mono text-[10px] text-slate-200">
          <p>● nhận bài: sẵn sàng</p>
          <p>● xử lý: ổn định</p>
          <p>● báo cáo: sẵn sàng</p>
        </div>
      </div>
    </motion.div>
  );
};
