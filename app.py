import streamlit as st
import copy
import os

from main_backend import (
    call_vertex, generate_title, generate_outline_from_desc,
    generate_ppt_from_outline, generate_doc_from_outline,
    generate_single_image, summarize_long_text, extract_text
)

# ---------------- Streamlit Config ----------------
st.set_page_config(page_title="AI Productivity Suite", layout="wide")
st.title("AI Productivity Suite")

# ---------------- Helpers ----------------
def render_outline_preview(outline_data, mode="ppt"):
    if not outline_data:
        st.info("No outline available.")
        return False

    title = outline_data.get("title", "Untitled")
    items = outline_data.get("slides", []) if mode == "ppt" else outline_data.get("sections", [])
    st.subheader(f"📝 Preview Outline: {title}")

    for idx, item in enumerate(items, start=1):
        item_title = item.get("title", f"{'Slide' if mode=='ppt' else 'Section'} {idx}")
        item_desc = item.get("description", "")
        with st.expander(f"{'Slide' if mode=='ppt' else 'Section'} {idx}: {item_title}", expanded=False):
            st.markdown(item_desc.replace("\n", "\n\n"))
    return len(items) > 0

# ---------------- Session State ----------------
defaults = {
    "messages": [],
    "outline_chat": None,
    "outline_mode": None,  # "ppt" or "doc"
    "generated_files": [],
    "summary_text": None,
    "summary_title": None,
    "doc_chat_history": [],
    "outline_from_summary": None,
    "generated_images": [],  # store past generated images
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ---------------- Chat History ----------------
for role, content in st.session_state.messages:
    with st.chat_message(role):
        st.markdown(content)

# ---------------- General Chat ----------------
if prompt := st.chat_input("Type a message, ask for a PPT, DOC, or Image ..."):
    st.session_state.messages.append(("user", prompt))
    text = prompt.lower()

    try:
        if "ppt" in text or "presentation" in text or "slides" in text:
            with st.spinner("Generating PPT outline..."):
                title = generate_title(prompt)
                slides = generate_outline_from_desc(prompt, 5, mode="ppt")
                st.session_state.outline_chat = {"title": title, "slides": slides}
                st.session_state.outline_mode = "ppt"
                st.session_state.messages.append(("assistant", "✅ PPT outline generated! Preview below."))

        elif "doc" in text or "document" in text or "report" in text or "pages" in text or "sections" in text:
            with st.spinner("Generating DOC outline..."):
                title = generate_title(prompt)
                sections = generate_outline_from_desc(prompt, 5, mode="doc")
                st.session_state.outline_chat = {"title": title, "sections": sections}
                st.session_state.outline_mode = "doc"
                st.session_state.messages.append(("assistant", "✅ DOC outline generated! Preview below."))

        elif "image" in text or "picture" in text or "photo" in text:
            with st.spinner("Generating Image..."):
                filepath = generate_single_image(prompt)
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                filename = os.path.basename(filepath)

                st.session_state.generated_images.append({"filename": filename, "content": img_bytes})
                st.image(img_bytes, caption=filename, use_container_width=True)
                st.download_button("⬇️ Download Image", data=img_bytes, file_name=filename, mime="image/png")
                st.session_state.messages.append(("assistant", "✅ Image generated!"))

        else:
            reply = call_vertex(prompt)
            st.session_state.messages.append(("assistant", reply))

    except Exception as e:
        st.session_state.messages.append(("assistant", f"⚠️ Error: {e}"))

    st.rerun()

# ---------------- Outline Preview + Actions ----------------
if st.session_state.outline_chat:
    mode = st.session_state.outline_mode
    outline = st.session_state.outline_chat

    render_outline_preview(outline, mode=mode)

    new_title = st.text_input("📌 Edit Title", value=outline.get("title", "Untitled"), key=f"title_{mode}")
    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"✅ Generate {mode.upper()}"):
            with st.spinner(f"Generating {mode.upper()}..."):
                try:
                    outline_to_use = copy.deepcopy(outline)
                    outline_to_use["title"] = new_title.strip() if new_title else outline_to_use["title"]

                    if mode == "ppt":
                        filename = generate_ppt_from_outline(outline_to_use["title"], outline_to_use["slides"])
                        mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    else:
                        filename = generate_doc_from_outline(outline_to_use["title"], outline_to_use["sections"])
                        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                    with open(filename, "rb") as f:
                        file_bytes = f.read()

                    st.success(f"✅ {mode.upper()} generated successfully!")
                    st.download_button(
                        f"⬇️ Download {mode.upper()}",
                        data=file_bytes,
                        file_name=os.path.basename(filename),
                        mime=mime,
                        key=f"download_{mode}_{filename}"
                    )

                    st.session_state.generated_files.append({"type": mode, "filename": filename, "content": file_bytes})
                    st.session_state.outline_chat = None
                except Exception as e:
                    st.error(f"❌ Generation error: {e}")

# ---------------- Document Upload ----------------
uploaded_file = st.file_uploader("📂 Upload a document", type=["pdf", "docx", "txt", "md"])

if uploaded_file is not None:
    with st.spinner("Processing uploaded file..."):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        text = extract_text(tmp_path, uploaded_file.name)
        os.remove(tmp_path)

        if text.strip():
            summary = summarize_long_text(text)
            st.session_state.summary_text = summary
            st.session_state.summary_title = generate_title(summary) or os.path.splitext(uploaded_file.name)[0]
            st.success(f"✅ Document uploaded! Suggested Title: **{st.session_state.summary_title}**")
        else:
            st.error("❌ Unsupported or empty file.")

# ---------------- Chat with Document ----------------
if st.session_state.summary_text:
    st.markdown("💬 **Chat with your uploaded document**")

    for role, content in st.session_state.doc_chat_history:
        with st.chat_message(role):
            st.markdown(content)

    if doc_prompt := st.chat_input("Ask a question about the uploaded document..."):
        st.session_state.doc_chat_history.append(("user", doc_prompt))
        try:
            reply = call_vertex(f"Document:\n{st.session_state.summary_text}\n\nQuestion:\n{doc_prompt}")
            st.session_state.doc_chat_history.append(("assistant", reply))
        except Exception as e:
            st.session_state.doc_chat_history.append(("assistant", f"⚠️ Error: {e}"))
        st.rerun()
