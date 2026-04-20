"use client";

import React, { useState } from "react";
import { Database, FileUp, RefreshCw, RotateCcw, Settings, Trash2 } from "lucide-react";
import type { SystemSettings } from "@/types";

const SYSTEM_VERSION = "2.1.0";

interface SettingsTabProps {
  settings: SystemSettings;
  updateSetting: <K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) => void;
  settingsLastUpdated: string;
  onClearHistory: () => void;
  onExportSettings: () => void;
  onImportSettings: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onRestoreDefaults: () => void;
  onResetSession: () => void;
}

export const SettingsTab = ({
  settings,
  updateSetting,
  settingsLastUpdated,
  onClearHistory,
  onExportSettings,
  onImportSettings,
  onRestoreDefaults,
  onResetSession,
}: SettingsTabProps) => {
  return (
    <div className="max-w-5xl mx-auto space-y-8 py-2">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-gray-100 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Cài đặt hệ thống</h1>
          <p className="text-sm text-gray-400 mt-1.5 leading-relaxed">
            Quản trị cấu hình vận hành và đồng bộ dữ liệu cục bộ cho nền tảng.
          </p>
        </div>
        <div className="px-3 py-1.5 rounded-full bg-blue-50 border border-blue-100 flex items-center gap-2 shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-[11px] font-bold text-blue-700 uppercase tracking-wider">Phiên bản {SYSTEM_VERSION}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Vận hành & Trải nghiệm */}
        <div className="card-elevated p-6 md:p-8 space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
              <Settings className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="text-[15px] font-bold text-gray-800">Tùy chọn vận hành</h2>
          </div>

          <div className="space-y-4">
            <SettingToggle 
              label="Tự động mở kết quả"
              description="Chuyển sang tab lịch sử ngay khi có điểm."
              checked={settings.autoOpenHistory}
              onChange={(v) => updateSetting("autoOpenHistory", v)}
            />
            <SettingToggle 
              label="Thông báo hệ thống"
              description="Hiển thị thông báo Toast khi thao tác."
              checked={settings.enableNotifications}
              onChange={(v) => updateSetting("enableNotifications", v)}
            />
            <SettingToggle 
              label="Ghi nhớ sinh viên"
              description="Lưu MSSV và Họ tên cho lần nộp tiếp theo."
              checked={settings.rememberStudent}
              onChange={(v) => updateSetting("rememberStudent", v)}
            />
          </div>

          <div className="pt-4 space-y-2">
            <label className="text-[13px] font-bold text-gray-700 uppercase tracking-tight">Thời gian chờ xử lý</label>
            <div className="relative group">
              <input
                type="number"
                min={120}
                max={600}
                className="input h-11 pr-12 group-hover:border-blue-300 transition-colors"
                value={Math.round(settings.requestTimeoutMs / 1000)}
                onChange={(e) =>
                  updateSetting(
                    "requestTimeoutMs",
                    Math.max(120000, (Number(e.target.value) || 120) * 1000)
                  )
                }
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-400">giây</span>
            </div>
            <p className="text-[11px] text-gray-400 italic">Mặc định: 120s . Tối đa: 600s .</p>
          </div>
        </div>

        {/* Quản trị dữ liệu & Nâng cao */}
        <div className="space-y-6">
          {/* Data Actions */}
          <div className="card-elevated p-6 md:p-8 border-l-4 border-l-red-500">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center text-red-600">
                <Trash2 className="w-4 h-4" />
              </div>
              <h3 className="text-[15px] font-bold text-gray-800">Vùng nguy hiểm</h3>
            </div>
            <p className="text-[13px] text-gray-500 mb-6 leading-relaxed">
              Xóa sạch lịch sử kết quả đã lưu trong trình duyệt này. Thao tác này <b>không thể hoàn tác</b> và không ảnh hưởng dữ liệu máy chủ.
            </p>
            <button
              onClick={onClearHistory}
              className="w-full h-11 rounded-xl bg-red-50 text-red-600 text-[13px] font-bold border border-red-100 hover:bg-red-600 hover:text-white hover:border-red-600 transition-all active:scale-[0.98]"
            >
              Dọn dẹp bộ nhớ đệm
            </button>
          </div>

          {/* Configuration Sync */}
          <div className="card-elevated p-6 md:p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
                <Database className="w-4 h-4" />
              </div>
              <h3 className="text-[15px] font-bold text-gray-800">Cấu hình & Đồng bộ</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-3 mb-6">
              <button onClick={onExportSettings} className="flex flex-col items-center justify-center p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:border-blue-200 hover:shadow-md transition-all group">
                <Database className="w-5 h-5 text-gray-400 group-hover:text-blue-600 mb-2" />
                <span className="text-[12px] font-bold text-gray-600">Xuất JSON</span>
              </button>
              <label htmlFor="settings-import" className="flex flex-col items-center justify-center p-4 rounded-xl border border-gray-100 bg-gray-50/50 hover:bg-white hover:border-blue-200 hover:shadow-md transition-all cursor-pointer group text-center">
                <FileUp className="w-5 h-5 text-gray-400 group-hover:text-blue-600 mb-2" />
                <span className="text-[12px] font-bold text-gray-600">Nhập JSON</span>
              </label>
              <input id="settings-import" type="file" accept="application/json" className="hidden" onChange={onImportSettings} />
            </div>

            <div className="flex gap-2">
              <button 
                onClick={onResetSession}
                className="flex-1 h-11 flex items-center justify-center gap-2 rounded-xl bg-white border border-gray-200 text-[12px] font-bold text-gray-600 hover:text-blue-600 hover:border-blue-200 transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Làm mới phiên
              </button>
              <button 
                onClick={onRestoreDefaults}
                className="flex-1 h-11 flex items-center justify-center gap-2 rounded-xl bg-white border border-gray-200 text-[12px] font-bold text-gray-600 hover:text-red-500 hover:border-red-200 transition-all"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Mặc định
              </button>
            </div>
          </div>
        </div>
      </div>

      <footer className="text-center pt-8 border-t border-gray-50">
        <p className="text-[11px] text-gray-400">
          Cập nhật thông số lần cuối: <span className="font-semibold text-gray-500">{settingsLastUpdated}</span>
        </p>
      </footer>
    </div>
  );
};

interface SettingToggleProps {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}

const SettingToggle = ({ label, description, checked, onChange }: SettingToggleProps) => (
  <div className="flex items-center justify-between gap-4 group">
    <div className="flex-1">
      <p className="text-[14px] font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">{label}</p>
      <p className="text-[11px] text-gray-400 mt-0.5">{description}</p>
    </div>
    <label className="relative inline-flex items-center cursor-pointer">
      <input 
        type="checkbox" 
        className="sr-only peer" 
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
    </label>
  </div>
);
