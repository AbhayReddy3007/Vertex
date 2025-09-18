# app.py
import streamlit as st
import requests
import base64

# ✅ Page setup
st.set_page_config(page_title="Imagen 4 Generator", layout="centered")
st.title("Image Generator (Vertex AI - Imagen 4)")

# ✅ Hardcoded backend URL (your FastAPI backend)
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
            except:
                err = resp.text
            st.error(f"Backend error ({resp.status_code}): {err}")
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
