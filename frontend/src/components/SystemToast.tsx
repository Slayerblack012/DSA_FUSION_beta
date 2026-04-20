import React from "react";
import toast from "react-hot-toast";
import { Brain, Settings } from "lucide-react";

interface SystemToastProps {
  t: any;
  message: string;
}

export const SystemToast = ({ t, message }: SystemToastProps) => {
  return (
    <div
      className={`${
        t.visible ? "animate-in fade-in zoom-in" : "animate-out fade-out zoom-out"
      } max-w-sm w-full bg-white/95 backdrop-blur-md shadow-[0_20px_50px_rgba(0,0,0,0.15)] rounded-3xl pointer-events-auto ring-1 ring-black/5 overflow-hidden transition-all duration-300`}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-blue-50 rounded-xl">
              <Brain className="w-5 h-5 text-blue-600" />
            </div>
            <span className="text-[15px] font-bold text-blue-600 tracking-tight">
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
          <p className="text-[14px] text-gray-700 leading-relaxed font-medium">
            {message}
          </p>
        </div>

        {/* Action */}
        <div className="flex justify-center">
          <button
            onClick={() => toast.dismiss(t.id)}
            className="w-full py-3 px-4 text-[13px] font-black uppercase tracking-widest text-slate-900 hover:bg-slate-50 active:bg-slate-100 rounded-2xl transition-all border border-slate-100"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};

export const showSystemToast = (message: string) => {
  toast.custom((t) => <SystemToast t={t} message={message} />, {
     duration: 5000,
     position: "top-right"
  });
};
