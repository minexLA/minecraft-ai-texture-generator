import {
  GenerateResponse,
  GenerateTextureParams,
  ProvidersResponse,
  ReprocessParams,
} from "../types/texture";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

const FALLBACK_PROVIDERS: ProvidersResponse = {
  default_provider: "mock",
  providers: [
    {
      id: "upload_only",
      name: "Custom Image Upload Only (No AI — Pipeline Only)",
      description:
        "Skips AI inference and runs the pixel-art pipeline directly on your uploaded image.",
      configured: true,
      supports_img2img: true,
      is_default: false,
    },
    {
      id: "pollinations",
      name: "Pollinations.ai (Flux — Free, No Key Needed)",
      description:
        "Free cloud AI image generation powered by Flux via Pollinations.ai.",
      configured: true,
      supports_img2img: false,
      is_default: false,
    },
    {
      id: "mock",
      name: "Built-in Procedural Synthesizer (Offline Ready)",
      description:
        "Deterministic procedural sprite & seamless texture generator for instant testing.",
      configured: true,
      supports_img2img: true,
      is_default: true,
    },
    {
      id: "openai",
      name: "OpenAI (gpt-image-1 / DALL-E)",
      description: "Cloud inference via OpenAI Images API (OPENAI_API_KEY).",
      configured: false,
      supports_img2img: true,
      is_default: false,
    },
    {
      id: "gemini",
      name: "Google Gemini / Imagen 3",
      description: "Cloud inference via Google Imagen API (GEMINI_API_KEY).",
      configured: false,
      supports_img2img: false,
      is_default: false,
    },
    {
      id: "replicate",
      name: "Replicate (Flux / SDXL)",
      description: "Cloud inference via Replicate API (REPLICATE_API_TOKEN).",
      configured: false,
      supports_img2img: true,
      is_default: false,
    },
    {
      id: "fal",
      name: "Fal.ai (Flux / Fast SDXL)",
      description: "Fast cloud inference via Fal.ai REST API (FAL_KEY).",
      configured: false,
      supports_img2img: true,
      is_default: false,
    },
    {
      id: "local_sd",
      name: "Local Stable Diffusion (A1111 / Diffusers API)",
      description: "Local GPU inference via LOCAL_SD_URL (http://127.0.0.1:7860).",
      configured: false,
      supports_img2img: true,
      is_default: false,
    },
  ],
};

export async function fetchProviders(): Promise<ProvidersResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/providers`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return FALLBACK_PROVIDERS;
    }
    return (await response.json()) as ProvidersResponse;
  } catch {
    return FALLBACK_PROVIDERS;
  }
}

export async function generateTexture(
  params: GenerateTextureParams
): Promise<GenerateResponse> {
  const formData = new FormData();
  formData.append("prompt", params.prompt);
  formData.append("mode", params.mode);
  formData.append("size", String(params.size));
  formData.append("provider", params.provider);
  formData.append("strength", String(params.strength));
  formData.append("palette_colors", String(params.paletteColors));
  formData.append("alpha_threshold", String(params.alphaThreshold));
  formData.append("response_format", "json");

  if (params.referenceImage) {
    formData.append("reference_image", params.referenceImage);
  }

  const response = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = `Generation failed (${response.status})`;
    try {
      const errJson = (await response.json()) as { detail?: string };
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Ignore JSON parse errors on fallback error body
    }
    throw new Error(errorDetail);
  }

  return (await response.json()) as GenerateResponse;
}

export async function reprocessTexture(
  params: ReprocessParams
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/reprocess`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    let errorDetail = `Reprocess failed (${response.status})`;
    try {
      const errJson = (await response.json()) as { detail?: string };
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errorDetail);
  }

  return (await response.json()) as GenerateResponse;
}

