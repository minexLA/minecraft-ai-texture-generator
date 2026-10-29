import React, { useRef, useState } from "react";
import {
  Box,
  ClipboardPaste,
  Cpu,
  ImagePlus,
  Layers,
  Palette,
  Sparkles,
  Sword,
  Trash2,
} from "lucide-react";
import {
  ProviderId,
  ProviderInfo,
  TargetSize,
  TextureMode,
} from "../types/texture";

interface ControlPanelProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  mode: TextureMode;
  onModeChange: (mode: TextureMode) => void;
  size: TargetSize;
  onSizeChange: (size: TargetSize) => void;
  provider: ProviderId;
  providers: ProviderInfo[];
  onProviderChange: (provider: ProviderId) => void;
  strength: number;
  onStrengthChange: (strength: number) => void;
  paletteColors: number;
  onPaletteColorsChange: (colors: number) => void;
  referenceImage: File | null;
  referencePreviewUrl: string | null;
  onReferenceImageChange: (file: File | null) => void;
  onGenerate: () => void;
  onProcessUploadOnly: () => void;
  isGenerating: boolean;
}

const ITEM_PRESETS = [
  "Enchanted ruby sword with golden hilt",
  "Emerald crystal pickaxe",
  "Glowing golden apple",
  "Amethyst battle axe",
];

const BLOCK_PRESETS = [
  "Mossy cobblestone wall",
  "Glowing diamond ore in deep stone",
  "Cracked nether brick tiles",
  "Chiseled obsidian runic block",
];

const SIZES: TargetSize[] = [16, 32, 64];
const PALETTE_COUNTS = [8, 16, 24, 32, 48];

export const ControlPanel: React.FC<ControlPanelProps> = ({
  prompt,
  onPromptChange,
  mode,
  onModeChange,
  size,
  onSizeChange,
  provider,
  providers,
  onProviderChange,
  strength,
  onStrengthChange,
  paletteColors,
  onPaletteColorsChange,
  referenceImage,
  referencePreviewUrl,
  onReferenceImageChange,
  onGenerate,
  onProcessUploadOnly,
  isGenerating,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [pasteHint, setPasteHint] = useState<string | null>(null);
  const presets = mode === "item" ? ITEM_PRESETS : BLOCK_PRESETS;
  const activeProviderInfo = providers.find((p) => p.id === provider);
  const isUploadOnly = provider === "upload_only";

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setPasteHint(null);
    onReferenceImageChange(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0] ?? null;
    if (file) {
      setPasteHint(null);
      onReferenceImageChange(file);
    }
  };

  const handlePasteFromClipboardButton = async () => {
    setPasteHint(null);
    if (!navigator.clipboard || !navigator.clipboard.read) {
      setPasteHint("Press Ctrl+V (or Cmd+V) anywhere on the page to paste an image.");
      return;
    }
    try {
      const clipboardItems = await navigator.clipboard.read();
      for (const item of clipboardItems) {
        const imageType = item.types.find((t) => t.startsWith("image/"));
        if (imageType) {
          const blob = await item.getType(imageType);
          const ext = (imageType.split("/")[1] || "png").replace("jpeg", "jpg");
          const file = new File([blob], `clipboard_pasted.${ext}`, {
            type: imageType,
          });
          onReferenceImageChange(file);
          return;
        }
      }
      setPasteHint("No image found in clipboard. Copy an image first or press Ctrl+V.");
    } catch {
      setPasteHint("Press Ctrl+V (or Cmd+V) anywhere on the page to paste your copied image.");
    }
  };

  const handleClearReference = () => {
    onReferenceImageChange(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating) return;
    if (isUploadOnly) {
      if (!referenceImage) return;
      onProcessUploadOnly();
      return;
    }
    if (!prompt.trim()) return;
    onGenerate();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-xl"
    >
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Asset Type
        </label>
        <div className="grid grid-cols-2 gap-2.5">
          <button
            type="button"
            onClick={() => onModeChange("item")}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl border text-sm font-medium transition ${
              mode === "item"
                ? "bg-emerald-500/15 border-emerald-500 text-emerald-300 shadow-sm"
                : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
            }`}
          >
            <Sword className="w-4 h-4" />
            <span>Item</span>
          </button>
          <button
            type="button"
            onClick={() => onModeChange("block")}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl border text-sm font-medium transition ${
              mode === "block"
                ? "bg-emerald-500/15 border-emerald-500 text-emerald-300 shadow-sm"
                : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
            }`}
          >
            <Box className="w-4 h-4" />
            <span>Block</span>
          </button>
        </div>
        <p className="mt-1.5 text-xs text-slate-500">
          {mode === "item"
            ? "Removes background and applies hard alpha edges."
            : "Generates an opaque, repeatable block texture."}
        </p>
      </div>

      <div>
        <label
          htmlFor="texture-prompt"
          className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2"
        >
          Prompt {isUploadOnly && "(Optional)"}
        </label>
        <textarea
          id="texture-prompt"
          rows={3}
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder={
            isUploadOnly
              ? "Optional when converting an uploaded image..."
              : mode === "item"
              ? "e.g. Enchanted ruby sword with golden hilt..."
              : "e.g. Mossy cobblestone wall..."
          }
          className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
          required={!isUploadOnly}
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {presets.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => onPromptChange(preset)}
              className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg border border-slate-700/70 transition"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span>Resolution</span>
        </label>
        <div className="grid grid-cols-3 gap-2">
          {SIZES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSizeChange(s)}
              className={`py-2 px-3 rounded-xl border font-mono text-sm font-semibold transition ${
                size === s
                  ? "bg-emerald-500/15 border-emerald-500 text-emerald-300"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
              }`}
            >
              {s}x{s}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Palette className="w-3.5 h-3.5 text-emerald-400" />
            <span>Color Palette</span>
          </label>
          <span className="text-xs font-mono text-emerald-400 font-semibold">
            {paletteColors} colors
          </span>
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {PALETTE_COUNTS.map((count) => (
            <button
              key={count}
              type="button"
              onClick={() => onPaletteColorsChange(count)}
              className={`py-1.5 rounded-lg border font-mono text-xs transition ${
                paletteColors === count
                  ? "bg-emerald-500/15 border-emerald-500 text-emerald-300 font-semibold"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
              }`}
            >
              {count}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label
          htmlFor="provider-select"
          className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2"
        >
          <Cpu className="w-3.5 h-3.5 text-emerald-400" />
          <span>Provider</span>
        </label>
        <select
          id="provider-select"
          value={provider}
          onChange={(e) => onProviderChange(e.target.value as ProviderId)}
          className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} {!p.configured ? "(Not configured)" : ""}
            </option>
          ))}
        </select>
        {activeProviderInfo && (
          <p className="mt-1.5 text-xs text-slate-500">
            {activeProviderInfo.description}
          </p>
        )}
      </div>

      <div className="pt-1 border-t border-slate-800/80">
        <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          <ImagePlus className="w-3.5 h-3.5 text-emerald-400" />
          <span>Source / Reference Image</span>
        </label>

        {!referenceImage ? (
          <div className="space-y-2">
            <label
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className="flex flex-col items-center justify-center border-2 border-dashed border-slate-800 hover:border-emerald-500/60 rounded-xl p-4 cursor-pointer bg-slate-950/40 transition"
            >
              <ImagePlus className="w-6 h-6 text-slate-500 mb-1" />
              <span className="text-xs text-slate-300 font-medium text-center">
                Click to upload, Drag &amp; Drop, or press Ctrl+V to paste
              </span>
              <span className="text-[11px] text-slate-500 mt-0.5 text-center">
                Supports PNG, JPG, JFIF / JIFF, WebP, BMP, GIF (max 5 MB)
              </span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.jfif,.jiff,.pjpeg,.webp,.bmp,.gif,image/png,image/jpeg,image/jfif,image/webp,image/bmp,image/gif"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>

            <button
              type="button"
              onClick={handlePasteFromClipboardButton}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 text-slate-200 text-xs font-medium transition"
            >
              <ClipboardPaste className="w-3.5 h-3.5 text-emerald-400" />
              <span>Paste Image from Clipboard (Ctrl+V)</span>
            </button>

            {pasteHint && (
              <p className="text-[11px] text-amber-300/90 text-center">
                {pasteHint}
              </p>
            )}
          </div>
        ) : (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                {referencePreviewUrl && (
                  <img
                    src={referencePreviewUrl}
                    alt="Uploaded reference preview"
                    className="w-12 h-12 rounded-lg object-cover border border-slate-700 checkerboard-bg"
                  />
                )}
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-200 truncate">
                    {referenceImage.name}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {(referenceImage.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleClearReference}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-rose-950/70 text-slate-400 hover:text-rose-300 border border-slate-800 transition"
                title="Remove uploaded image"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            {/* Direct Pixel Pipeline Button (No AI) */}
            <button
              type="button"
              disabled={isGenerating}
              onClick={onProcessUploadOnly}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 font-semibold text-xs shadow-md transition"
            >
              <Layers className="w-4 h-4" />
              <span>
                Process Uploaded Image Only (Skip AI → {size}x{size})
              </span>
            </button>

            {!isUploadOnly && (
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Denoising / Prompt Strength (For AI Img2Img)</span>
                  <span className="font-mono text-emerald-400">
                    {Math.round(strength * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={0.95}
                  step={0.05}
                  value={strength}
                  onChange={(e) => onStrengthChange(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>Keep Reference Structure</span>
                  <span>Follow Text Prompt More</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Generate Submit Button */}
      <button
        type="submit"
        disabled={
          isGenerating ||
          (isUploadOnly ? !referenceImage : !prompt.trim())
        }
        className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 font-semibold text-sm shadow-lg shadow-emerald-500/10 transition"
      >
        <Sparkles className="w-4 h-4" />
        <span>
          {isGenerating
            ? "Processing Pixel Pipeline..."
            : isUploadOnly
            ? `Process Custom Image to ${size}x${size} ${mode === "item" ? "Item" : "Block"} (No AI)`
            : `Generate ${size}x${size} ${mode === "item" ? "Item" : "Block"} Texture`}
        </span>
      </button>
    </form>
  );
};

