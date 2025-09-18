# main.py
import os
import base64
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Google Cloud SDK
# pip install google-cloud-aiplatform google-auth
from google.cloud import aiplatform
from google.cloud.aiplatform.generative_models import GenerativeModel

app = FastAPI(title="ImageGen - Vertex AI Imagen 4 Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Config
GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
IMAGEN_MODEL = os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")


class GenerateRequest(BaseModel):
    prompt: str
    seed: Optional[int] = None


@app.on_event("startup")
def init_vertex():
    """Initialize Vertex AI SDK on startup."""
    aiplatform.init(project=GCP_PROJECT, location=GCP_LOCATION)


@app.get("/")
def root():
    return {
        "status": "ok",
        "note": "POST to /generate-image with JSON {prompt, optional seed}",
        "current_model": IMAGEN_MODEL,
    }


@app.post("/generate-image")
def generate_image(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required.")

    try:
        # Load Imagen 4 model
        model = GenerativeModel(IMAGEN_MODEL)

        # Generate images (Imagen 4 auto-handles dimensions & steps)
        result = model.generate_images(
            prompt=req.prompt,
            number_of_images=1,   # fixed
            seed=req.seed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vertex AI error: {str(e)}")

    images_out = []
    for img in result.images:
        # Vertex AI may return either image.bytes or image.uri depending on SDK version
        bts = None
        if hasattr(img, "bytes") and img.bytes:
            bts = img.bytes
        elif hasattr(img, "image_bytes") and img.image_bytes:
            bts = img.image_bytes
        elif hasattr(img, "uri") and img.uri:
            # If it’s a GCS URI, you’d need to fetch from storage — skipping here
            raise HTTPException(status_code=500, detail="Imagen returned a URI instead of raw bytes.")
        else:
            continue

        if bts:
            b64 = base64.b64encode(bts).decode("utf-8")
            images_out.append({"b64": b64, "mime": "image/png"})

    if not images_out:
        raise HTTPException(status_code=500, detail="No image data returned from Imagen 4.")

    return JSONResponse(content={"images": images_out, "model": IMAGEN_MODEL})
