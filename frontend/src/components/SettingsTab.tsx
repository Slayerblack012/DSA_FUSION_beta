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
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Cài đặt hệ thống</h1>
        <p className="text-sm text-gray-500 mt-1">
          Tùy chỉnh trải nghiệm và dữ liệu cục bộ cho cổng chấm điểm.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-5">
        <div className="card-elevated p-6 space-y-4">
          <h2 className="label-sm flex items-center gap-2">
            <Settings className="w-4 h-4 text-blue-600" /> Tùy chọn vận hành
          </h2>

          <div className="rounded-lg border border-orange-100 bg-orange-50/60 px-3 py-2">
            <p className="text-[11px] font-semibold text-orange-700">System Version</p>
            <p className="text-sm font-bold text-orange-900">v{SYSTEM_VERSION}</p>
            <p className="text-[11px] text-orange-700 mt-1">
              Cập nhật lần cuối: {settingsLastUpdated}
            </p>
          </div>

          <label className="flex items-center justify-between text-sm text-gray-700">
            <span>Tự mở tab kết quả sau khi chấm</span>
            <input
              type="checkbox"
              checked={settings.autoOpenHistory}
              onChange={(e) => updateSetting("autoOpenHistory", e.target.checked)}
            />
          </label>

          <label className="flex items-center justify-between text-sm text-gray-700">
            <span>Bật thông báo toast</span>
            <input
              type="checkbox"
              checked={settings.enableNotifications}
              onChange={(e) => updateSetting("enableNotifications", e.target.checked)}
            />
          </label>

          <label className="flex items-center justify-between text-sm text-gray-700">
            <span>Lưu thông tin sinh viên</span>
            <input
              type="checkbox"
              checked={settings.rememberStudent}
              onChange={(e) => updateSetting("rememberStudent", e.target.checked)}
            />
          </label>

          <div>
            <label className="label">Thời gian chờ xử lý (giây)</label>
            <input
              type="number"
              min={120}
              max={600}
              step={1}
              className="input"
              value={Math.round(settings.requestTimeoutMs / 1000)}
              onChange={(e) =>
                updateSetting(
                  "requestTimeoutMs",
                  Math.max(120000, (Number(e.target.value) || 120) * 1000)
                )
              }
            />
          </div>

          <p className="text-xs text-gray-400 pt-2 border-t border-gray-100">
            Cài đặt được lưu tại localStorage trên trình duyệt hiện tại.
          </p>
        </div>

        <div className="card p-5 border-red-100 bg-red-50/40">
          <h3 className="label-sm text-red-600 mb-3">Vùng thao tác dữ liệu</h3>
          <p className="text-sm text-red-700 mb-4">
            Xóa toàn bộ lịch sử kết quả đã lưu trên trình duyệt này. Không ảnh hưởng dữ liệu trên
            máy chủ.
          </p>
          <button
            onClick={onClearHistory}
            className="h-10 px-4 rounded-lg bg-red-600 text-white text-sm font-semibold hover:bg-red-700 transition-colors inline-flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Xóa lịch sử kết quả
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          onClick={onExportSettings}
          className="btn-secondary h-11 px-4 justify-center"
        >
          <Database className="w-4 h-4" /> Xuất file cài đặt
        </button>
        <label
          htmlFor="settings-import"
          className="btn-secondary h-11 px-4 justify-center cursor-pointer"
        >
          <FileUp className="w-4 h-4" /> Nhập file cài đặt
        </label>
        <input
          id="settings-import"
          type="file"
          accept="application/json"
          className="hidden"
          onChange={onImportSettings}
        />
        <button
          onClick={onRestoreDefaults}
          className="btn-secondary h-11 px-4 justify-center"
        >
          <RotateCcw className="w-4 h-4" /> Khôi phục mặc định
        </button>
        <button
          onClick={onResetSession}
          className="btn-secondary h-11 px-4 justify-center"
        >
          <RefreshCw className="w-4 h-4" /> Reset phiên hiện tại
        </button>
      </div>
    </div>
  );
};
