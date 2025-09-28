"use client";

import type { Language } from "@/types/editor";

interface Props {
  value: Language;
  onChange: (lang: Language) => void;
}

export default function LanguageSelect({ value, onChange }: Props) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Language:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Language)}
        className="border rounded px-2 py-1 text-sm"
      >
        <option value="python">Python</option>
        <option value="r">R</option>
      </select>
    </div>
  );
}
