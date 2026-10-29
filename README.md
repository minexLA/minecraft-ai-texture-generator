# Minecraft Texture Generator

Web application for generating and converting 16x16, 32x32, and 64x64 Minecraft item and block textures from text prompts or custom images.

## Features

- **Item & Block Modes**:
  - **Item**: Strips backgrounds with `rembg` and applies binary alpha thresholding (`alpha > 128 ? 255 : 0`) to prevent semi-transparent borders in-game.
  - **Block**: Generates opaque tileable textures with a live 3x3 repeating preview grid.
- **Pixel Post-Processing Pipeline**:
  - Nearest-neighbor downscaling (`16x16`, `32x32`, `64x64`).
  - MedianCut palette quantization (`8` to `48` colors, no dithering) while preserving binary alpha.
- **Direct Image Conversion (No AI)**:
  - Upload or paste (`Ctrl+V`) any existing image (`.png`, `.jpg`, `.jfif`, `.jiff`, `.webp`, `.bmp`, `.gif`) to convert it directly into a Minecraft texture without calling an AI model.
- **Pluggable AI Providers**:
  - **Pollinations (Flux)** — works out of the box without an API key
  - **Procedural (Offline)** — built-in local sprite and pattern synthesizer
  - **Hugging Face** (`HF_TOKEN`)
  - **OpenAI** (`OPENAI_API_KEY`)
  - **Google Gemini / Imagen** (`GEMINI_API_KEY`)
  - **Replicate** (`REPLICATE_API_TOKEN`)
  - **Fal.ai** (`FAL_KEY`)
  - **Local Stable Diffusion** (`LOCAL_SD_URL`, e.g., Automatic1111 / Forge / Diffusers API)
- **Built-in Pixel Editor**:
  - Touch up pixels directly in the browser with Pencil, Eraser, Eyedropper, color picker, grid overlay, Undo/Redo, and 1:1 PNG export.

## Getting Started

### Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

- **Web UI**: http://127.0.0.1:3000
- **API Docs**: http://127.0.0.1:8000/docs

### Local Development

**Backend (Python 3.10+)**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend (Node 20+)**

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.

## Running Tests

```bash
cd backend
pytest tests/
```
