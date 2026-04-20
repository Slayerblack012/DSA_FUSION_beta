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
    const pTimer = setInterval(() => setProgress((p) => Math.min(p + 1, 99)), 80);
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
      className="fixed inset-0 z-[200] bg-white/95 backdrop-blur-sm flex flex-col items-center justify-center motion-perf"
    >
      {/* Scanner */}
      <div className="relative mb-12">
        <div className="w-20 h-20 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center relative overflow-hidden">
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
          <p className="text-4xl font-bold text-gray-900 tabular-nums">{progress}%</p>
          <div className="w-full h-1 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              animate={{ width: `${progress}%` }}
              className="h-full bg-blue-600 rounded-full"
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ y: 4, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -4, opacity: 0 }}
            className="text-sm text-gray-500 font-medium flex items-center justify-center gap-2"
          >
            <Terminal className="w-3.5 h-3.5 text-blue-600" />
            {GRADING_STEPS[step]}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* Status dots */}
      <div className="absolute bottom-12 right-12 hidden lg:block text-left opacity-40">
        <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Trang thai he thong
        </p>
        <div className="space-y-1 text-[10px] text-gray-400 font-mono">
          <p>● nhan bai: san sang</p>
          <p>● xu ly: on dinh</p>
          <p>● bao cao: san sang</p>
        </div>
      </div>
    </motion.div>
  );
};
