import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X } from "lucide-react";
import type { ConfirmDialogState } from "@/types";

interface ConfirmDialogProps {
  dialog: ConfirmDialogState;
  onClose: () => void;
  onConfirm: () => void;
}

export const ConfirmDialog = ({ dialog, onClose, onConfirm }: ConfirmDialogProps) => {
  return (
    <AnimatePresence>
      {dialog.open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[300] bg-slate-900/40 backdrop-blur-md flex items-center justify-center p-4 sm:p-6"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 400 }}
            className="bg-white rounded-[32px] shadow-[0_32px_64px_-16px_rgba(0,0,0,0.2)] max-w-sm w-full overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with Icon */}
            <div className="pt-8 pb-4 flex flex-col items-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <AlertTriangle className="w-8 h-8 text-red-600" strokeWidth={2.5} />
              </div>
              <h3 className="text-xl font-black text-slate-900 tracking-tight">{dialog.title}</h3>
            </div>
            
            {/* Message */}
            <div className="px-8 pb-8 text-center">
              <p className="text-[15px] font-medium text-slate-500 leading-relaxed">
                {dialog.message}
              </p>
            </div>

            {/* Actions */}
            <div className="px-6 pb-6 flex flex-col gap-2">
              <button
                onClick={() => {
                  onConfirm();
                  onClose();
                }}
                className="w-full py-4 rounded-2xl bg-red-600 text-white text-[15px] font-black uppercase tracking-wider hover:bg-red-700 active:scale-[0.98] transition-all shadow-lg shadow-red-200"
              >
                {dialog.confirmText}
              </button>
              <button
                onClick={onClose}
                className="w-full py-4 rounded-2xl bg-slate-50 text-slate-400 text-[13px] font-bold uppercase tracking-widest hover:text-slate-600 hover:bg-slate-100 transition-all"
              >
                Bỏ qua
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
