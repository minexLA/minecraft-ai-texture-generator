import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Download,
  Eraser,
  Grid,
  Pencil,
  Pipette,
  Redo2,
  RotateCcw,
  Undo2,
} from "lucide-react";
import { EditorTool, TargetSize, TextureMode } from "../types/texture";

interface PixelCanvasEditorProps {
  initialImageB64: string;
  size: TargetSize;
  mode: TextureMode;
  palette: string[];
  onCanvasUpdate: (dataUrl: string) => void;
}

function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) => n.toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function hexToRgb(hex: string): [number, number, number] {
  const cleaned = hex.replace("#", "").trim();
  if (cleaned.length !== 6) return [255, 255, 255];
  const num = parseInt(cleaned, 16);
  if (Number.isNaN(num)) return [255, 255, 255];
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

export const PixelCanvasEditor: React.FC<PixelCanvasEditorProps> = ({
  initialImageB64,
  size,
  mode,
  palette,
  onCanvasUpdate,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [tool, setTool] = useState<EditorTool>("pencil");
  const [activeColor, setActiveColor] = useState<string>(
    palette[0] || "#34d399"
  );
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [isDrawing, setIsDrawing] = useState<boolean>(false);
  const [hoverCoord, setHoverCoord] = useState<{ x: number; y: number } | null>(
    null
  );

  // Undo / Redo ImageData stack
  const [history, setHistory] = useState<ImageData[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);

  useEffect(() => {
    if (palette.length > 0) {
      setActiveColor((prev) => (palette.includes(prev) ? prev : palette[0]));
    }
  }, [palette]);

  // Load initial base64 image onto the exact-resolution canvas
  const loadInitialImage = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !initialImageB64) return;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = size;
      canvas.height = size;
      ctx.imageSmoothingEnabled = false;
      ctx.clearRect(0, 0, size, size);
      ctx.drawImage(img, 0, 0, size, size);
      const snap = ctx.getImageData(0, 0, size, size);
      setHistory([snap]);
      setHistoryIndex(0);
      onCanvasUpdate(canvas.toDataURL("image/png"));
    };
    img.src = initialImageB64.startsWith("data:")
      ? initialImageB64
      : `data:image/png;base64,${initialImageB64}`;
  }, [initialImageB64, size, onCanvasUpdate]);

  useEffect(() => {
    loadInitialImage();
  }, [loadInitialImage]);

  const getPixelCoordinates = (
    e: React.MouseEvent<HTMLCanvasElement>
  ): { x: number; y: number } | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const relX = e.clientX - rect.left;
    const relY = e.clientY - rect.top;
    const x = Math.floor((relX / rect.width) * size);
    const y = Math.floor((relY / rect.height) * size);
    if (x < 0 || x >= size || y < 0 || y >= size) return null;
    return { x, y };
  };

  const applyToolAtPixel = (x: number, y: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    const imageData = ctx.getImageData(0, 0, size, size);
    const idx = (y * size + x) * 4;

    if (tool === "eyedropper") {
      const a = imageData.data[idx + 3];
      if (a > 0) {
        const hex = rgbToHex(
          imageData.data[idx],
          imageData.data[idx + 1],
          imageData.data[idx + 2]
        );
        setActiveColor(hex);
      }
      setTool("pencil");
      return;
    }

    if (tool === "eraser") {
      imageData.data[idx] = 0;
      imageData.data[idx + 1] = 0;
      imageData.data[idx + 2] = 0;
      imageData.data[idx + 3] = 0;
    } else {
      const [r, g, b] = hexToRgb(activeColor);
      imageData.data[idx] = r;
      imageData.data[idx + 1] = g;
      imageData.data[idx + 2] = b;
      imageData.data[idx + 3] = 255;
    }

    ctx.putImageData(imageData, 0, 0);
    onCanvasUpdate(canvas.toDataURL("image/png"));
  };

  const commitHistorySnapshot = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    const snapshot = ctx.getImageData(0, 0, size, size);
    const sliced = history.slice(0, historyIndex + 1);
    setHistory([...sliced, snapshot]);
    setHistoryIndex(sliced.length);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getPixelCoordinates(e);
    if (!coords) return;
    if (tool === "eyedropper") {
      applyToolAtPixel(coords.x, coords.y);
      return;
    }
    setIsDrawing(true);
    applyToolAtPixel(coords.x, coords.y);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getPixelCoordinates(e);
    setHoverCoord(coords);
    if (!isDrawing || !coords) return;
    applyToolAtPixel(coords.x, coords.y);
  };

  const handleMouseUp = () => {
    if (isDrawing) {
      setIsDrawing(false);
      commitHistorySnapshot();
    }
  };

  const handleUndo = () => {
    if (historyIndex <= 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const nextIdx = historyIndex - 1;
    ctx.putImageData(history[nextIdx], 0, 0);
    setHistoryIndex(nextIdx);
    onCanvasUpdate(canvas.toDataURL("image/png"));
  };

  const handleRedo = () => {
    if (historyIndex >= history.length - 1) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const nextIdx = historyIndex + 1;
    ctx.putImageData(history[nextIdx], 0, 0);
    setHistoryIndex(nextIdx);
    onCanvasUpdate(canvas.toDataURL("image/png"));
  };

  const handleDownloadExactPng = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = `minecraft_${mode}_${size}x${size}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">
            Pixel Editor ({size}x{size})
          </h2>
          <p className="text-xs text-slate-400">
            Click or drag on the canvas to edit individual pixels
          </p>
        </div>

        <button
          type="button"
          onClick={handleDownloadExactPng}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-xs shadow-md transition"
        >
          <Download className="w-4 h-4" />
          <span>Export {size}x{size} PNG</span>
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-950 border border-slate-800 rounded-xl p-2.5">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setTool("pencil")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              tool === "pencil"
                ? "bg-emerald-500 text-slate-950 font-semibold"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Pencil className="w-3.5 h-3.5" />
            <span>Pencil</span>
          </button>

          <button
            type="button"
            onClick={() => setTool("eraser")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              tool === "eraser"
                ? "bg-emerald-500 text-slate-950 font-semibold"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Eraser className="w-3.5 h-3.5" />
            <span>Eraser</span>
          </button>

          <button
            type="button"
            onClick={() => setTool("eyedropper")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              tool === "eyedropper"
                ? "bg-emerald-500 text-slate-950 font-semibold"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <Pipette className="w-3.5 h-3.5" />
            <span>Eyedropper</span>
          </button>

          <div className="h-5 w-px bg-slate-800 mx-1" />

          {/* Color input */}
          <label className="flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded-lg bg-slate-900 border border-slate-800">
            <input
              type="color"
              value={activeColor}
              onChange={(e) => {
                setActiveColor(e.target.value);
                setTool("pencil");
              }}
              className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
            />
            <span className="font-mono text-xs text-slate-300">
              {activeColor.toUpperCase()}
            </span>
          </label>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setShowGrid((prev) => !prev)}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs border transition ${
              showGrid
                ? "bg-slate-800 border-emerald-500/50 text-emerald-300"
                : "bg-slate-900 border-slate-800 text-slate-400"
            }`}
            title="Toggle pixel grid overlay"
          >
            <Grid className="w-3.5 h-3.5" />
            <span>Grid</span>
          </button>

          <button
            type="button"
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-slate-300 border border-slate-800 transition"
            title="Undo"
          >
            <Undo2 className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 text-slate-300 border border-slate-800 transition"
            title="Redo"
          >
            <Redo2 className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={loadInitialImage}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition"
            title="Reset to generated output"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Canvas & Swatches Layout */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
        {/* Upscaled Interactive Pixel Canvas */}
        <div className="md:col-span-7 flex flex-col items-center bg-slate-950 border border-slate-800 rounded-xl p-4">
          <div className="relative w-72 h-72 sm:w-80 sm:h-80 rounded-lg overflow-hidden border border-slate-700 checkerboard-bg select-none">
            <canvas
              ref={canvasRef}
              width={size}
              height={size}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={() => {
                setHoverCoord(null);
                handleMouseUp();
              }}
              className="w-full h-full pixelated cursor-crosshair block"
            />
            {showGrid && (
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  backgroundImage:
                    "linear-gradient(to right, rgba(255,255,255,0.12) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.12) 1px, transparent 1px)",
                  backgroundSize: `${100 / size}% ${100 / size}%`,
                }}
              />
            )}
          </div>
          <div className="mt-2 flex items-center justify-between w-full text-xs text-slate-400 font-mono px-2">
            <span>
              Resolution: {size}x{size} px
            </span>
            <span>
              {hoverCoord
                ? `Cursor: (${hoverCoord.x}, ${hoverCoord.y})`
                : "Hover canvas to inspect pixel"}
            </span>
          </div>
        </div>

        {/* Extracted Quantized Palette Swatches */}
        <div className="md:col-span-5 bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Extracted Palette ({palette.length})
            </span>
            <span className="text-[11px] text-slate-500">Click to select</span>
          </div>

          <div className="grid grid-cols-6 gap-2 max-h-56 overflow-y-auto pr-1">
            {palette.map((hex) => (
              <button
                key={hex}
                type="button"
                onClick={() => {
                  setActiveColor(hex);
                  setTool("pencil");
                }}
                className={`h-8 rounded-lg border transition ${
                  activeColor.toLowerCase() === hex.toLowerCase() &&
                  tool === "pencil"
                    ? "border-white ring-2 ring-emerald-400 scale-105"
                    : "border-slate-700 hover:scale-105"
                }`}
                style={{ backgroundColor: hex }}
                title={hex.toUpperCase()}
              />
            ))}
          </div>

          <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 space-y-1">
            <p>
              • <strong className="text-slate-300">Binary Alpha:</strong>{" "}
              Eraser sets pixel alpha strictly to <code className="text-emerald-400">0</code>.
            </p>
            <p>
              • <strong className="text-slate-300">Resource Pack Ready:</strong>{" "}
              Exports raw {size}x{size} PNG without scaling artifacts.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

