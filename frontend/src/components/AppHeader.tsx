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
    <header className="surface-glass enterprise-panel sticky top-0 z-50 flex h-16 items-center justify-between px-4 md:px-6">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2.5">
          <div className="brand-gradient flex h-9 w-9 items-center justify-center rounded-xl shadow-[0_12px_30px_rgba(37,99,235,0.24)]">
            <GraduationCap className="w-4.5 h-4.5 text-white" />
          </div>
          <div className="leading-tight">
            <span className="block text-[15px] font-semibold text-slate-900">DSA Autograder</span>
            <span className="block text-[11px] uppercase tracking-[0.18em] text-slate-500">Enterprise EdTech</span>
          </div>
        </div>
        <nav className="hidden md:flex gap-1">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`rounded-full px-3.5 py-2 text-[13px] font-medium transition-all duration-200 ${
                activeTab === item.id
                  ? "bg-blue-600 text-white shadow-[0_10px_24px_rgba(37,99,235,0.22)]"
                  : "text-slate-500 hover:bg-white/70 hover:text-slate-900"
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-full border border-white/70 bg-white/75 px-3 py-1.5 shadow-sm">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100">
            <User className="w-3.5 h-3.5 text-slate-500" />
          </div>
          <span className="text-[13px] font-medium text-slate-600">
            {studentName || "Sinh viên"}
          </span>
        </div>
        <button className="relative flex h-9 w-9 items-center justify-center rounded-full border border-white/70 bg-white/70 text-slate-400 shadow-sm transition-colors hover:bg-white hover:text-slate-600">
          <Bell className="w-4 h-4" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white" />
        </button>
        <button
          onClick={() => setActiveTab("settings")}
          className="relative flex h-9 w-9 items-center justify-center rounded-full border border-white/70 bg-white/70 text-slate-400 shadow-sm transition-colors hover:bg-white hover:text-slate-600"
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
    <div className="surface-glass sticky top-16 z-40 px-3 py-2 md:hidden">
      <div className="grid grid-cols-2 gap-2">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`flex h-10 items-center justify-center gap-1.5 rounded-xl text-[12px] font-medium transition-all duration-200 ${
              activeTab === item.id
                ? "bg-blue-600 text-white shadow-[0_10px_22px_rgba(37,99,235,0.22)]"
                : "border border-white/70 bg-white/70 text-slate-500"
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
    <div className="surface-glass fixed bottom-0 left-0 right-0 z-50 flex items-stretch md:hidden">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => setActiveTab(item.id)}
          className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2.5 text-[11px] font-medium transition-all duration-200 ${
            activeTab === item.id
              ? "bg-blue-50 text-blue-600"
              : "bg-transparent text-slate-400"
          }`}
        >
          <item.icon className="w-5 h-5" />
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
};
