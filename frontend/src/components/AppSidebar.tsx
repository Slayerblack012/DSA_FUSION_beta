"use client";

import React from "react";
import { ClipboardList, Activity, Settings } from "lucide-react";
import { motion } from "framer-motion";
import type { AppTab } from "@/types";

const SIDEBAR_ITEMS: Array<{ label: string; id: AppTab; icon: React.ElementType }> = [
  { label: "Nộp bài", id: "submit", icon: ClipboardList },
  { label: "Kết quả", id: "history", icon: Activity },
  { label: "Cài đặt", id: "settings", icon: Settings },
];

interface SidebarProps {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
}

export const AppSidebar = ({ activeTab, setActiveTab }: SidebarProps) => {
  return (
    <aside className="surface-glass enterprise-panel w-60 flex flex-col py-6 px-4 hidden overflow-y-auto thin-scroll lg:fixed lg:left-0 lg:top-16 lg:z-30 lg:flex lg:h-[calc(100vh-64px)]">
      <p className="section-title px-4 mb-4">Danh mục</p>
      <div className="space-y-1">
        {SIDEBAR_ITEMS.map((item, i) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={i}
              onClick={() => setActiveTab(item.id)}
              className={`sidebar-link w-full relative transition-all duration-200 group ${
                isActive ? "bg-blue-50/80 text-blue-700 font-bold shadow-[0_10px_24px_rgba(37,99,235,0.08)]" : "hover:bg-white/70 text-slate-500"
              }`}
            >
              <item.icon className={`w-4.5 h-4.5 shrink-0 ${isActive ? "text-blue-600" : "text-slate-400 group-hover:text-blue-500"}`} />
              <span className="truncate">{item.label}</span>
              {isActive && (
                <motion.div
                  layoutId="sidebar-active-indicator"
                  className="absolute left-0 w-1 h-6 bg-blue-600 rounded-r-full"
                  transition={{ type: "spring", bounce: 0, duration: 0.3 }}
                />
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
};
