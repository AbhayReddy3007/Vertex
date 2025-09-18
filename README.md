This is my ppt_generator.py
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE, MSO_VERTICAL_ANCHOR
import re
from PIL import Image

def clean_title_text(title: str) -> str:
    """Clean up titles for slides."""
    if not title:
        return "Presentation"
    title = re.sub(r"\s+", " ", title.strip())
    return title

def resize_image(image_path, max_width=800, max_height=600):
    """Resize image to fit inside max_width × max_height (in pixels)."""
    try:
        img = Image.open(image_path)
        img.thumbnail((max_width, max_height))
        resized_path = image_path.replace(".png", "_resized.png")
        img.save(resized_path, "PNG")
        return resized_path
    except Exception as e:
        print(f"⚠️ Could not resize image {image_path}: {e}")
        return image_path

def create_ppt(title, points, filename="output.pptx", images=None):
    prs = Presentation()

    # Brand Colors
    PRIMARY_PURPLE = RGBColor(94, 42, 132)
    SECONDARY_TEAL = RGBColor(0, 185, 163)
    TEXT_DARK = RGBColor(40, 40, 40)
    BG_LIGHT = RGBColor(244, 244, 244)

    title = clean_title_text(title)

    # Title Slide
    slide_layout = prs.slide_layouts[5]  # blank
    slide = prs.slides.add_slide(slide_layout)
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = PRIMARY_PURPLE

    # Title TextBox
    left, top, width, height = Inches(1), Inches(2), Inches(8), Inches(3)
    textbox = slide.shapes.add_textbox(left, top, width, height)
    tf = textbox.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    tf.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
    p = tf.add_paragraph()
    p.text = title
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    # Content Slides
    for idx, item in enumerate(points, start=1):
        key_point = clean_title_text(item.get("title", ""))
        description = item.get("description", "")

        slide = prs.slides.add_slide(prs.slide_layouts[5])

        # Alternate background
        bg_color = BG_LIGHT if idx % 2 == 0 else RGBColor(255, 255, 255)
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = bg_color

        # Title
        left, top, width, height = Inches(0.8), Inches(0.5), Inches(8), Inches(1.5)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        tf.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
        p = tf.add_paragraph()
        p.text = key_point
        p.font.size = Pt(30)
        p.font.bold = True
        p.font.color.rgb = PRIMARY_PURPLE
        p.alignment = PP_ALIGN.LEFT

        # Accent underline
        shape = slide.shapes.add_shape(
            1, Inches(0.8), Inches(1.6), Inches(3), Inches(0.1)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = SECONDARY_TEAL
        shape.line.fill.background()

        # Description bullets
        if description:
            left, top, width, height = Inches(1), Inches(2.2), Inches(5), Inches(4)
            textbox = slide.shapes.add_textbox(left, top, width, height)
            tf = textbox.text_frame
            tf.word_wrap = True
            for line in description.split("\n"):
                if line.strip():
                    bullet = tf.add_paragraph()
                    bullet.text = line.strip()
                    bullet.font.size = Pt(22)
                    bullet.font.color.rgb = TEXT_DARK
                    bullet.level = 0

        # Add image if available
        if images and idx - 1 < len(images) and images[idx - 1]:
            try:
                img_path = resize_image(images[idx - 1], max_width=800, max_height=600)
                slide.shapes.add_picture(img_path, Inches(6), Inches(2.2), Inches(3.5), Inches(3))
            except Exception as e:
                print(f"⚠️ Could not add image to slide {idx}: {e}")

        # Footer watermark
        textbox = slide.shapes.add_textbox(Inches(0.5), Inches(6.8), Inches(8), Inches(0.3))
        tf = textbox.text_frame
        p = tf.add_paragraph()
        p.text = "Generated with AI"
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor(150, 150, 150)
        p.alignment = PP_ALIGN.RIGHT

    prs.save(filename)
    return filename

This is my doc_generator.py
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import re

def clean_title_text(title: str) -> str:
    """Clean up titles for document sections."""
    if not title:
        return "Document"
    title = re.sub(r"\s+", " ", title.strip())
    return title

def create_doc(title, sections, filename="output.docx", images=None):
    """
    Create a Word Document with optional images.
    sections: list of {"title": str, "description": str}
    images: list of file paths or None (one per section)
    """
    doc = Document()

    # Title Page
    doc.add_heading(clean_title_text(title), level=0)
    doc.add_paragraph()

    # Sections
    for idx, section in enumerate(sections, start=1):
        sec_title = clean_title_text(section.get("title", f"Section {idx}"))
        description = section.get("description", "")

        heading = doc.add_heading(sec_title, level=1)
        heading.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

        # Add text paragraphs
        for para in description.split("\n"):
            if para.strip():
                p = doc.add_paragraph(para.strip())
                p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
                run = p.runs[0]
                run.font.size = Pt(11)

        # Add image if available
        if images and idx - 1 < len(images) and images[idx - 1]:
            try:
                doc.add_paragraph()
                doc.add_picture(images[idx - 1], width=Inches(5.5))
                last_paragraph = doc.paragraphs[-1]
                last_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                doc.add_paragraph()
            except Exception as e:
                print(f"⚠️ Failed to insert image for section {idx}: {e}")

        doc.add_page_break()

    # Footer watermark
    section = doc.sections[-1]
    footer = section.footer
    footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    run = footer_para.add_run("Generated with AI")
    run.font.size = Pt(9)

    doc.save(filename)
    return filename


