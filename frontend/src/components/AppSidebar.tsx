"use client";

import React from "react";
import { ClipboardList, Activity, Settings } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
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
    <aside className="w-56 bg-white border-r border-gray-100 flex flex-col py-5 px-3 hidden lg:flex overflow-y-auto thin-scroll lg:fixed lg:top-14 lg:left-0 lg:h-[calc(100vh-56px)] lg:z-30">
      <p className="section-title px-3 mb-3">Danh mục</p>
      {SIDEBAR_ITEMS.map((item, i) => {
        const isActive = activeTab === item.id;
        return (
          <button
            key={i}
            onClick={() => setActiveTab(item.id)}
            className={`sidebar-link w-full relative ${isActive ? "text-blue-600 font-semibold" : ""}`}
          >
            {isActive && (
              <motion.div
                layoutId="sidebar-active-pill"
                className="absolute inset-0 bg-blue-50/80 rounded-lg -z-10"
                transition={{ type: "spring", bounce: 0.25, duration: 0.5 }}
              />
            )}
            <item.icon className={`w-4 h-4 ${isActive ? "text-blue-600" : ""}`} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </aside>
  );
};
