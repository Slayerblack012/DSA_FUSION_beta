import React from "react";
import toast, { type Toast } from "react-hot-toast";
import { Brain, Trash2, X } from "lucide-react";
import { motion } from "framer-motion";

interface SystemToastProps {
  t: Toast;
  message: string;
  variant?: "default" | "destructive" | "success" | "warning";
}

export const SystemToast = ({ t, message, variant = "default" }: SystemToastProps) => {
  const isDestructive = variant === "destructive" || variant === "warning";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ 
        opacity: t.visible ? 1 : 0, 
        y: t.visible ? 0 : -8
      }}
      transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
      className={`surface-glass motion-perf max-w-sm w-full rounded-3xl pointer-events-auto shadow-[0_12px_30px_rgba(15,23,42,0.12)] ring-1 ${
        isDestructive ? "ring-red-200" : "ring-black/5"
      } overflow-hidden`}
    >
      <div className="p-4.5 sm:p-5">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <div className={`rounded-2xl border p-2.5 ${isDestructive ? "border-red-100 bg-red-100" : "border-blue-100 bg-blue-50"}`}>
              {isDestructive ? (
                <Trash2 className="w-5 h-5 text-red-600" />
              ) : (
                <Brain className="w-5 h-5 text-blue-600" />
              )}
            </div>
            <span className={`text-[14px] font-black uppercase tracking-[0.18em] ${isDestructive ? "text-red-600" : "text-blue-700"}`}>
              Thông báo hệ thống
            </span>
          </div>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="rounded-full p-1.5 text-slate-400 transition-colors hover:bg-slate-100"
            aria-label="Đóng thông báo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="mb-5 px-1">
          <p className={`text-[14px] ${isDestructive ? "text-red-700" : "text-slate-700"} leading-relaxed font-medium`}>
            {message}
          </p>
        </div>

        <div className="flex justify-center">
          <button
            onClick={() => toast.dismiss(t.id)}
            className={`w-full rounded-2xl border px-4 py-3 text-[13px] font-black uppercase tracking-[0.18em] transition-all ${
              isDestructive
                ? "border-red-200 bg-red-100 text-red-900 hover:bg-red-200"
                : "border-slate-100 bg-slate-50 text-slate-900 hover:bg-slate-100"
            }`}
          >
            Đóng
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export const showSystemToast = (message: string, variant: "default" | "destructive" | "success" = "default") => {
  toast.custom((t) => <SystemToast t={t} message={message} variant={variant} />, {
     duration: 5000,
     removeDelay: 180,
     position: "top-right"
  });
};
