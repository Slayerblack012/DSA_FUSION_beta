"use client";

import Editor from "@monaco-editor/react";

interface MonacoEditorProps {
  code: string;
  onChange: (value: string) => void;
}

export default function MonacoEditorComponent({ code, onChange }: MonacoEditorProps) {
  return (
    <Editor
      height="100%"
      defaultLanguage="python"
      theme="vs-light"
      value={code}
      onChange={(value) => onChange(value || "")}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
        fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
        padding: { top: 16 },
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        cursorBlinking: "smooth",
      }}
    />
  );
}
