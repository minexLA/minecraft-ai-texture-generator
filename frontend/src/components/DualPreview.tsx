import React from "react";
import { ArrowRight, Sparkles, Terminal } from "lucide-react";
import { TargetSize, TextureMode } from "../types/texture";

interface DualPreviewProps {
  rawImageB64: string;
  processedDataUrl: string;
  wrappedPrompt: string;
  size: TargetSize;
  mode: TextureMode;
  paletteCount: number;
}

export const DualPreview: React.FC<DualPreviewProps> = ({
  rawImageB64,
  processedDataUrl,
  wrappedPrompt,
  size,
  mode,
  paletteCount,
}) => {
  const rawSrc = rawImageB64.startsWith("data:")
    ? rawImageB64
    : `data:image/png;base64,${rawImageB64}`;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span>Preview</span>
          </h2>
          <p className="text-xs text-slate-400">
            Source image vs. downscaled &amp; quantized texture
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
            {mode.toUpperCase()}
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/40 text-emerald-300">
            {size}x{size}
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300">
            {paletteCount} colors
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-11 gap-4 items-center">
        <div className="sm:col-span-5 bg-slate-950 border border-slate-800 rounded-xl p-3 flex flex-col items-center">
          <span className="text-xs font-medium text-slate-400 mb-2">
            Source Image
          </span>
          <div className="w-44 h-44 rounded-lg overflow-hidden border border-slate-800 checkerboard-bg flex items-center justify-center">
            <img
              src={rawSrc}
              alt="Source output"
              className="w-full h-full object-contain"
            />
          </div>
          <span className="mt-2 text-[11px] text-slate-500">
            Pre-pipeline input
          </span>
        </div>

        <div className="sm:col-span-1 flex flex-col items-center justify-center text-emerald-400">
          <ArrowRight className="w-6 h-6 rotate-90 sm:rotate-0" />
        </div>

        <div className="sm:col-span-5 bg-slate-950 border border-emerald-500/40 rounded-xl p-3 flex flex-col items-center">
          <span className="text-xs font-medium text-emerald-300 mb-2">
            Pixel Output ({size}x{size})
          </span>
          <div className="w-44 h-44 rounded-lg overflow-hidden border border-slate-800 checkerboard-bg flex items-center justify-center p-2">
            <img
              src={processedDataUrl}
              alt="Processed pixel art output"
              className="w-full h-full object-contain pixelated"
            />
          </div>
          <span className="mt-2 text-[11px] text-slate-400">
            Nearest-neighbor + quantized palette
          </span>
        </div>
      </div>

      {wrappedPrompt && (
        <div className="bg-slate-950/80 border border-slate-800/90 rounded-xl p-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-400 font-medium mb-1">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span>Prompt Details</span>
          </div>
          <p className="font-mono text-[11px] text-slate-300 break-words leading-relaxed">
            {wrappedPrompt}
          </p>
        </div>
      )}
    </div>
  );
};

