import os
import base64
import traceback
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

# ✅ Vertex AI imports (Imagen 4 works with this)
import vertexai
from vertexai.vision_models import ImageGenerationModel

# 🔹 Config
GCP_PROJECT = "my-project"   # replace with your project ID
GCP_LOCATION = "us-central1"
IMAGEN_MODEL = "imagen-4.0-generate-001"

# 🔹 Validate GOOGLE_APPLICATION_CREDENTIALS env
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not GOOGLE_CREDENTIALS or not os.path.exists(GOOGLE_CREDENTIALS):
    raise RuntimeError(
        "Missing or invalid GOOGLE_APPLICATION_CREDENTIALS environment variable."
    )

# ✅ Lifespan (runs once at startup)
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        print(f"✅ Vertex AI initialized for project={GCP_PROJECT}, location={GCP_LOCATION}")
    except Exception as e:
        tb = traceback.format_exc()
        print("🔥 Failed to initialize Vertex AI:\n", tb)
        raise
    yield

# ✅ Create FastAPI app
app = FastAPI(title="ImageGen - Vertex AI Imagen 4 Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Request body
class GenerateRequest(BaseModel):
    prompt: str
    seed: Optional[int] = None

# 🔹 Root health check
@app.get("/")
def root():
    return {
        "status": "ok",
        "note": "POST to /generate-image with JSON {prompt, optional seed}",
        "current_model": IMAGEN_MODEL,
        "project": GCP_PROJECT,
        "location": GCP_LOCATION,
    }

# 🔹 Image generation endpoint
@app.post("/generate-image")
def generate_image(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required.")

    try:
        model = ImageGenerationModel.from_pretrained(IMAGEN_MODEL)
        result = model.generate_images(
            prompt=req.prompt,
            number_of_images=1,
            seed=req.seed,
        )

        print("DEBUG result.images:", result.images)  # 👈 helps debug response

        images_out = []
        for idx, img in enumerate(result.images):
            bdata = None

            # Try Imagen 3 style
            if hasattr(img, "image_bytes") and img.image_bytes:
                bdata = img.image_bytes

            # Try Imagen 4 style
            elif hasattr(img, "bytes_data") and img.bytes_data:
                bdata = img.bytes_data

            # Last resort: raw protobuf object
            elif hasattr(img, "_pb") and hasattr(img._pb, "bytes_data"):
                bdata = img._pb.bytes_data

            if bdata:
                b64 = base64.b64encode(bdata).decode("utf-8")
                images_out.append({"b64": b64, "mime": "image/png"})
            else:
                print(f"⚠️ No usable bytes for image {idx}, raw object: {img}")

        if not images_out:
            raise HTTPException(
                status_code=500,
                detail="No image data returned from Imagen 4. (Possibly safety filter or SDK mismatch)"
            )

        return JSONResponse(content={"images": images_out, "model": IMAGEN_MODEL})

    except Exception as e:
        tb = traceback.format_exc()
        print("🔥 Vertex AI Exception Traceback:\n", tb)
        raise HTTPException(
            status_code=500,
            detail=f"Vertex AI error: {e}\nTraceback:\n{tb}"
        )

