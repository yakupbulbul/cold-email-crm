"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CopyBlockProps {
  code: string;
  title?: string;
}

export default function CopyBlock({ code, title }: CopyBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative rounded-xl overflow-hidden border border-[var(--border)]">
      {title && (
        <div className="flex items-center justify-between bg-[var(--surface-muted)] px-4 py-2 border-b border-[var(--border)]">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">{title}</span>
        </div>
      )}
      <div className="relative">
        <pre className="overflow-x-auto bg-[var(--sidebar)] px-4 py-4 text-sm leading-relaxed text-white font-mono whitespace-pre">
          {code}
        </pre>
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="absolute top-3 right-3 inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-semibold text-white/80 backdrop-blur transition-colors hover:bg-white/20 hover:text-white"
        >
          {copied ? (
            <>
              <Check size={14} />
              Copied!
            </>
          ) : (
            <>
              <Copy size={14} />
              Copy
            </>
          )}
        </button>
      </div>
    </div>
  );
}
