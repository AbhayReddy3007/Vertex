# main_backend.py
from ppt_generator import create_ppt
from doc_generator import create_doc

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.preview.vision_models import ImageGenerationModel

from typing import List
import os, re, datetime, tempfile, fitz, docx

# ---------------- CONFIG ----------------
PROJECT_ID = "drl-zenai-prod"
REGION = "us-central1"
vertexai.init(project=PROJECT_ID, location=REGION)

TEXT_MODEL = GenerativeModel("gemini-2.5-flash")
IMAGE_MODEL = ImageGenerationModel.from_pretrained("imagen-4.0-generate-001")


# ---------------- HELPERS ----------------
def extract_slide_count(description: str, default: int = 5) -> int:
    m = re.search(r"(\d+)\s*(slides?|sections?|pages?)", description, re.IGNORECASE)
    if m:
        total = int(m.group(1))
        return max(1, total - 1)
    return default - 1

def call_vertex(prompt: str) -> str:
    response = TEXT_MODEL.generate_content(prompt)
    return response.text.strip()

def generate_title(summary: str) -> str:
    prompt = f"""Read the following summary and create a short, clear, presentation-style title.
- Keep it under 12 words
- Do not include birth dates, long sentences, or excessive details
- Just give a clean title

Summary:
{summary}
"""
    return call_vertex(prompt).strip()

def parse_points(points_text: str):
    points = []
    current_title, current_content = None, []
    lines = [re.sub(r"[#*>`]", "", ln).rstrip() for ln in points_text.splitlines()]

    for line in lines:
        if not line or "Would you like" in line:
            continue
        m = re.match(r"^\s*(Slide|Section)\s*(\d+)\s*:\s*(.+)$", line, re.IGNORECASE)
        if m:
            if current_title:
                points.append({"title": current_title, "description": "\n".join(current_content)})
            current_title, current_content = m.group(3).strip(), []
            continue
        if line.strip().startswith("-"):
            text = line.lstrip("-").strip()
            if text:
                current_content.append(f"• {text}")
        elif line.strip().startswith(("•", "*")) or line.startswith("  "):
            text = line.lstrip("•*").strip()
            if text:
                current_content.append(f"- {text}")
        else:
            if line.strip():
                current_content.append(line.strip())

    if current_title:
        points.append({"title": current_title, "description": "\n".join(current_content)})
    return points

def extract_text(path: str, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        text_parts: List[str] = []
        doc = fitz.open(path)
        try:
            for page in doc:
                text_parts.append(page.get_text("text"))
        finally:
            doc.close()
        return "\n".join(text_parts)
    if name.endswith(".docx"):
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    if name.endswith(".txt"):
        for enc in ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""

def split_text(text: str, chunk_size: int = 8000, overlap: int = 300) -> List[str]:
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks

def generate_outline_from_desc(description: str, num_items: int, mode: str = "ppt"):
    if mode == "ppt":
        prompt = f"""Create a PowerPoint outline on: {description}.
Generate exactly {num_items} content slides (⚠️ excluding the title slide).
Do NOT include a title slide — I will handle it separately.
Start from Slide 1 as the first *content slide*.
Format strictly like this:
Slide 1: <Title>
- Bullet
- Bullet
"""
    else:
        prompt = f"""Create a detailed Document outline on: {description}.
Generate exactly {num_items} sections.
Each section should have:
- A section title
- 2–3 descriptive paragraphs (5–7 sentences each) of full prose.
Do NOT use bullet points.
Format strictly like this:
Section 1: <Title>
<Paragraph 1>
<Paragraph 2>
<Paragraph 3>
"""
    points_text = call_vertex(prompt)
    return parse_points(points_text)

def summarize_long_text(full_text: str) -> str:
    chunks = split_text(full_text)
    if len(chunks) <= 1:
        return call_vertex(f"Summarize the following text in detail:\n\n{full_text}")
    partial_summaries = []
    for idx, ch in enumerate(chunks, start=1):
        mapped = call_vertex(f"Summarize this part of a longer document:\n\n{ch}")
        partial_summaries.append(f"Chunk {idx}:\n{mapped.strip()}")
    combined = "\n\n".join(partial_summaries)
    return call_vertex(f"Combine these summaries into one clean, well-structured summary:\n\n{combined}")

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]', '_', name)

def clean_title(title: str) -> str:
    return re.sub(r"\s*\(.*?\)", "", title).strip()

def save_temp_image(image_bytes, idx, title):
    output_dir = os.path.join("generated_files", "images")
    os.makedirs(output_dir, exist_ok=True)
    safe_title = re.sub(r'[^A-Za-z0-9_.-]', '_', title)[:30]
    filename = f"{safe_title}_{idx}.png"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return filepath

def generate_images_for_points(points, mode="ppt"):
    images = []
    for idx, item in enumerate(points, start=1):
        img_prompt = (
            f"An illustration for a {mode.upper()} section titled '{item['title']}'. "
            f"Content: {item['description']}. "
            f"Style: professional, modern, clean, infographic look."
        )
        try:
            resp = IMAGE_MODEL.generate_images(prompt=img_prompt, number_of_images=1)
            if resp.images and hasattr(resp.images[0], "_image_bytes"):
                img_bytes = resp.images[0]._image_bytes
            else:
                img_bytes = None
            if img_bytes:
                img_path = save_temp_image(img_bytes, idx, item["title"])
                images.append(img_path)
            else:
                images.append(None)
        except Exception as e:
            print(f"⚠️ Image generation failed for {mode} {idx}: {e}")
            images.append(None)
    return images

def generate_ppt_from_outline(title: str, points: List[dict]):
    images = generate_images_for_points(points, mode="ppt")
    os.makedirs("generated_files", exist_ok=True)
    filename = os.path.join("generated_files", f"{sanitize_filename(title)}.pptx")
    create_ppt(title, points, filename=filename, images=images)
    return filename

def generate_doc_from_outline(title: str, points: List[dict]):
    images = generate_images_for_points(points, mode="doc")
    os.makedirs("generated_files", exist_ok=True)
    filename = os.path.join("generated_files", f"{sanitize_filename(title)}.docx")
    create_doc(title, points, filename=filename, images=images)
    return filename

def generate_single_image(prompt: str):
    resp = IMAGE_MODEL.generate_images(prompt=prompt, number_of_images=1)
    if resp.images and hasattr(resp.images[0], "_image_bytes"):
        img_bytes = resp.images[0]._image_bytes
    else:
        raise Exception("Image generation failed")
    output_dir = os.path.join("generated_files", "images")
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"generated_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    with open(filename, "wb") as f:
        f.write(img_bytes)
    return filename
