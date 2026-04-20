"use client";

import React from "react";
import { GraduationCap, Bell, Settings, User } from "lucide-react";
import type { AppTab } from "@/types";

const NAV_ITEMS: Array<{ label: string; id: AppTab; icon: React.ElementType }> = [
  { label: "Nộp bài", id: "submit", icon: GraduationCap },
  { label: "Kết quả", id: "history", icon: GraduationCap },
];

interface HeaderProps {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
  studentName: string;
}

export const AppHeader = ({ activeTab, setActiveTab, studentName }: HeaderProps) => {
  return (
    <header className="h-14 px-4 md:px-6 bg-white/90 backdrop-blur border-b border-gray-200/70 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 brand-gradient rounded-lg flex items-center justify-center shadow-sm">
            <GraduationCap className="w-4.5 h-4.5 text-white" />
          </div>
          <span className="font-semibold text-[15px] text-gray-900">DSA Autograder</span>
        </div>
        <nav className="hidden md:flex gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors ${
                activeTab === item.id
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-gray-50 py-1.5 px-3 rounded-lg border border-gray-100">
          <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-gray-500" />
          </div>
          <span className="text-[13px] font-medium text-gray-600">
            {studentName || "Sinh viên"}
          </span>
        </div>
        <button className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-50 relative">
          <Bell className="w-4 h-4" />
        </button>
        <button
          onClick={() => setActiveTab("settings")}
          className="w-8 h-8 rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-50 relative"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

export const MobileNav = ({
  activeTab,
  setActiveTab,
}: {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
}) => {
  return (
    <div className="md:hidden border-b border-gray-100 bg-white/95 backdrop-blur px-3 py-2">
      <div className="grid grid-cols-2 gap-2">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`h-9 rounded-lg text-[12px] font-medium flex items-center justify-center gap-1.5 transition-colors ${
              activeTab === item.id
                ? "bg-blue-600 text-white"
                : "bg-gray-50 text-gray-500"
            }`}
          >
            <item.icon className="w-3.5 h-3.5" />
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export const MobileBottomNav = ({
  activeTab,
  setActiveTab,
}: {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
}) => {
  return (
    <div className="fixed bottom-0 left-0 right-0 md:hidden bg-white border-t border-gray-200 flex items-stretch z-50">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => setActiveTab(item.id)}
          className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[11px] font-medium transition-colors ${
            activeTab === item.id
              ? "bg-blue-50 text-blue-600"
              : "bg-white text-gray-400"
          }`}
        >
          <item.icon className="w-5 h-5" />
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
};
