# main.py
import os
import base64
import traceback
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

# ✅ Vertex AI imports (Imagen 4 needs non-preview)
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

        images_out = []
        for img in result.images:
            # Imagen 4 sometimes uses image_bytes, sometimes bytes_data depending on SDK
            bdata = getattr(img, "image_bytes", None) or getattr(img, "bytes_data", None)
            if bdata:
                b64 = base64.b64encode(bdata).decode("utf-8")
                images_out.append({"b64": b64, "mime": "image/png"})

        if not images_out:
            raise HTTPException(
                status_code=500,
                detail="No image data returned from Imagen 4."
            )

        return JSONResponse(content={"images": images_out, "model": IMAGEN_MODEL})

    except Exception as e:
        tb = traceback.format_exc()
        print("🔥 Vertex AI Exception Traceback:\n", tb)
        raise HTTPException(
            status_code=500,
            detail=f"Vertex AI error: {e}\nTraceback:\n{tb}"
        )


This is my app.py
import streamlit as st
import requests
import base64

# ✅ Page setup
st.set_page_config(page_title="Imagen 4 Generator", layout="centered")
st.title("🖼️ Image Generator (Vertex AI - Imagen 4)")

# ✅ Hardcoded backend URL (FastAPI service must be running)
BACKEND_URL = "http://127.0.0.1:8000"

# ✅ Prompt input
prompt = st.text_area(
    "Enter your prompt",
    value="A futuristic cityscape at sunset, cinematic lighting, ultra-detailed"
)

if st.button("Generate"):
    if not prompt.strip():
        st.error("Please provide a prompt.")
    else:
        payload = {"prompt": prompt}
        try:
            with st.spinner("Generating image with Imagen 4..."):
                resp = requests.post(f"{BACKEND_URL}/generate-image", json=payload, timeout=180)
        except requests.RequestException as e:
            st.error(f"Failed to contact backend: {e}")
            st.stop()

        if resp.status_code != 200:
            try:
                err = resp.json()
            except Exception:
                err = resp.text
            st.error(f"Backend error ({resp.status_code}):")
            st.code(err, language="json")
        else:
            data = resp.json()
            images = data.get("images", [])
            if not images:
                st.error("No images returned.")
            else:
                st.success(f"Received image from model {data.get('model')}")
                for idx, art in enumerate(images):
                    b64 = art.get("b64")
                    mime = art.get("mime", "image/png")
                    if not b64:
                        continue
                    try:
                        img_bytes = base64.b64decode(b64)
                    except Exception as e:
                        st.error(f"Failed to decode image {idx}: {e}")
                        continue
                    st.image(img_bytes, caption=f"Image {idx+1}", use_column_width=True)
                    st.download_button(
                        label=f"Download image {idx+1}",
                        data=img_bytes,
                        file_name=f"gen_image_{idx+1}.png",
                        mime=mime,
                    )
