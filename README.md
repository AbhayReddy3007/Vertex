def should_generate_image(title: str, description: str) -> bool:
    """
    Decide if a slide/section really needs an image.
    Images should only be generated when a visual will
    add significant clarity (e.g., charts, diagrams, processes, comparisons).
    Avoid images for generic intro, text-heavy, or conclusion slides.
    """
    prompt = f"""
    You are deciding if an image is TRULY necessary for a presentation slide.

    Title: {title}
    Content: {description}

    Rules:
    - Say "YES" ONLY if a clear visual, diagram, chart, or illustration
      would help explain this content.
    - Say "NO" for general text slides, introductions, conclusions,
      or content that does not need a visual.
    - Avoid making every slide have an image.

    Answer strictly with YES or NO.
    """

    try:
        decision = call_vertex(prompt).strip().upper()
        return decision.startswith("Y")
    except:
        return False
