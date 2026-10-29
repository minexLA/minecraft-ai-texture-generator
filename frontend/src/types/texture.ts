export type TextureMode = "item" | "block";

export type TargetSize = 16 | 32 | 64;

export type ProviderId =
  | "upload_only"
  | "mock"
  | "pollinations"
  | "huggingface"
  | "openai"
  | "gemini"
  | "replicate"
  | "fal"
  | "local_sd";

export type EditorTool = "pencil" | "eraser" | "eyedropper";

export interface ProviderInfo {
  id: ProviderId;
  name: string;
  description: string;
  configured: boolean;
  supports_img2img: boolean;
  is_default: boolean;
}

export interface ProvidersResponse {
  default_provider: ProviderId;
  providers: ProviderInfo[];
}

export interface GenerateTextureParams {
  prompt: string;
  mode: TextureMode;
  size: TargetSize;
  provider: ProviderId;
  strength: number;
  paletteColors: number;
  alphaThreshold: number;
  referenceImage: File | null;
}

export interface GenerateResponse {
  processed_image_b64: string;
  raw_image_b64: string;
  wrapped_prompt: string;
  mode: TextureMode;
  size: TargetSize;
  provider: ProviderId;
  palette_colors: number;
  palette: string[];
}

export interface ReprocessParams {
  raw_image_b64: string;
  mode: TextureMode;
  size: TargetSize;
  palette_colors: number;
  alpha_threshold: number;
  strip_background?: boolean;
}

