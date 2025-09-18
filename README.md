#main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, datetime

import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# ---------------- CONFIG ----------------
PROJECT_ID = "drl-zenai-prod"
REGION = "us-central1"

vertexai.init(project=PROJECT_ID, location=REGION)

IMAGE_MODEL_NAME = "imagen-4.0-generate-001"
IMAGE_MODEL = ImageGenerationModel.from_pretrained(IMAGE_MODEL_NAME)

# ---------------- FASTAPI ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------
class ImageRequest(BaseModel):
    prompt: str

# ---------------- ROUTES ----------------
@app.post("/generate-image")
def generate_image(req: ImageRequest):
    try:
        resp = IMAGE_MODEL.generate_images(prompt=req.prompt, number_of_images=1)

        if resp.images and hasattr(resp.images[0], "_image_bytes"):
            img_bytes = resp.images[0]._image_bytes
        else:
            raise HTTPException(status_code=500, detail="No image data returned from Imagen 4")

        output_dir = os.path.join(os.path.dirname(__file__), "generated_images")
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.join(output_dir, f"image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

        with open(filename, "wb") as f:
            f.write(img_bytes)

        return FileResponse(filename, media_type="image/png", filename=os.path.basename(filename))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation error: {e}")

@app.get("/health")
def health():
    return {"status": "ok", "image_model": IMAGE_MODEL_NAME}

#app.py
import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"  # FastAPI backend URL

st.set_page_config(page_title="AI Image Generator", layout="wide")
st.title("🖼️ AI Image Generator")

# ---------------- STATE ----------------
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# ---------------- UI ----------------
prompt = st.text_area("✨ Enter your prompt to generate an image:", height=120)

if st.button("🚀 Generate Image"):
    if not prompt.strip():
        st.warning("Please enter a prompt!")
    else:
        with st.spinner("Generating image..."):
            try:
                resp = requests.post(f"{BACKEND_URL}/generate-image", json={"prompt": prompt}, timeout=180)
                if resp.status_code == 200:
                    img_bytes = resp.content
                    filename = resp.headers.get("content-disposition", "").split("filename=")[-1].strip('"') or "image.png"

                    st.image(img_bytes, caption=filename, use_container_width=True)
                    st.download_button(
                        "⬇️ Download Image",
                        data=img_bytes,
                        file_name=filename,
                        mime="image/png"
                    )

                    st.session_state.generated_images.append({"filename": filename, "content": img_bytes})

                else:
                    st.error(f"❌ Image generation failed: {resp.text}")
            except Exception as e:
                st.error(f"⚠️ Backend error: {e}")

# ---------------- HISTORY ----------------
if st.session_state.generated_images:
    st.subheader("📂 Past Generated Images")
    for i, img in enumerate(st.session_state.generated_images):
        with st.expander(f"Image {i+1}: {img['filename']}"):
            st.image(img["content"], caption=img["filename"], use_container_width=True)
            st.download_button(
                "⬇️ Download Again",
                data=img["content"],
                file_name=img["filename"],
                mime="image/png",
                key=f"download_img_{i}"
            )

