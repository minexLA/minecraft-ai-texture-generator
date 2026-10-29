import React, { useState } from "react";
import { Grid3X3 } from "lucide-react";
import { TargetSize, TextureMode } from "../types/texture";

interface TilePreview3x3Props {
  textureDataUrl: string;
  size: TargetSize;
  mode: TextureMode;
}

export const TilePreview3x3: React.FC<TilePreview3x3Props> = ({
  textureDataUrl,
  size,
  mode,
}) => {
  const [showTileSeams, setShowTileSeams] = useState<boolean>(false);
  const tiles = Array.from({ length: 9 }, (_, i) => i);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Grid3X3 className="w-4 h-4 text-emerald-400" />
            <span>
              3x3 Seamless Tiling Preview{" "}
              {mode === "block" ? "(Block Mode Active)" : "(Item Tiling Check)"}
            </span>
          </h2>
          <p className="text-xs text-slate-400">
            Verifies continuous repeating edges across adjacent {size}x{size} Minecraft blocks
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowTileSeams((prev) => !prev)}
          className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
            showTileSeams
              ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-300"
              : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
          }`}
        >
          {showTileSeams ? "Hide Tile Borders" : "Show Tile Borders"}
        </button>
      </div>

      <div className="flex flex-col items-center bg-slate-950 border border-slate-800 rounded-xl p-4">
        <div className="grid grid-cols-3 w-64 h-64 sm:w-72 sm:h-72 rounded-lg overflow-hidden border border-slate-700 checkerboard-bg">
          {tiles.map((idx) => (
            <div
              key={idx}
              className={
                showTileSeams ? "border border-emerald-400/40" : "border-0"
              }
            >
              <img
                src={textureDataUrl}
                alt={`Tile ${idx + 1}`}
                className="w-full h-full object-cover pixelated block"
              />
            </div>
          ))}
        </div>
        <span className="mt-2.5 text-xs text-slate-400">
          Updates live as you draw or erase pixels in the editor above
        </span>
      </div>
    </div>
  );
};

