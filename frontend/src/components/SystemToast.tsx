import React from "react";
import toast from "react-hot-toast";
import { Brain, Settings, Trash2, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

interface SystemToastProps {
  t: any;
  message: string;
  variant?: "default" | "destructive" | "success" | "warning";
}

export const SystemToast = ({ t, message, variant = "default" }: SystemToastProps) => {
  const isDestructive = variant === "destructive" || variant === "warning";
  
  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ 
        opacity: t.visible ? 1 : 0, 
        y: t.visible ? 0 : -20, 
        scale: t.visible ? 1 : 0.95
      }}
      transition={{ 
        duration: 0.25, 
        ease: [0.16, 1, 0.3, 1] 
      }}
      className={`max-w-sm w-full ${
        isDestructive ? "bg-red-50/95" : "bg-white/95"
      } backdrop-blur-md shadow-[0_20px_50px_rgba(0,0,0,0.15)] rounded-3xl pointer-events-auto ring-1 ${
        isDestructive ? "ring-red-200" : "ring-black/5"
      } overflow-hidden transition-all duration-300`}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className={`p-2 ${isDestructive ? "bg-red-100" : "bg-blue-50"} rounded-xl`}>
              {isDestructive ? (
                <Trash2 className="w-5 h-5 text-red-600" />
              ) : (
                <Brain className="w-5 h-5 text-blue-600" />
              )}
            </div>
            <span className={`text-[15px] font-bold ${isDestructive ? "text-red-600" : "text-blue-600"} tracking-tight`}>
              Thông báo hệ thống
            </span>
          </div>
          <button 
            onClick={() => toast.dismiss(t.id)}
            className="p-1.5 hover:bg-gray-100 rounded-full transition-colors text-gray-400"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="mb-6 px-1">
          <p className={`text-[14px] ${isDestructive ? "text-red-700" : "text-gray-700"} leading-relaxed font-medium`}>
            {message}
          </p>
        </div>

        {/* Action */}
        <div className="flex justify-center">
          <button
            onClick={() => toast.dismiss(t.id)}
            className={`w-full py-3 px-4 text-[13px] font-black uppercase tracking-widest ${
              isDestructive 
                ? "text-red-900 bg-red-100 hover:bg-red-200" 
                : "text-slate-900 bg-slate-50 hover:bg-slate-100"
            } rounded-2xl transition-all border ${isDestructive ? "border-red-200" : "border-slate-100"}`}
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
     position: "top-right"
  });
};
