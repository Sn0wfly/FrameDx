import anthropic

SYSTEM_PROMPT = (
    "You are a medical transcription editor. Fix any medical terminology errors "
    "in the following transcript segment from a radiology lecture. Only fix obvious "
    "medical term errors (e.g., 'new motor axe' → 'neumotórax', 'cole sister tommy' "
    "→ 'colecistectomía'). Preserve the original language (Spanish or English). "
    "Return ONLY the corrected text, nothing else."
)

BATCH_SIZE = 10


def correct_transcripts(
    texts: list[str],
    api_key: str,
    progress_callback=None,
) -> list[str]:
    """Send transcript texts to Claude API for medical term correction.

    Batches texts to minimize API calls.
    """
    if not api_key:
        raise ValueError("Anthropic API key is required for LLM correction")

    client = anthropic.Anthropic(api_key=api_key)
    corrected = []

    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch = texts[batch_start : batch_start + BATCH_SIZE]

        # Build a numbered batch prompt
        numbered = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(batch))
        user_prompt = (
            f"Correct the medical terminology in each numbered segment below. "
            f"Return each corrected segment on its own line, prefixed with the same number.\n\n"
            f"{numbered}"
        )

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            response_text = response.content[0].text
            lines = response_text.strip().split("\n")

            # Parse numbered responses back
            parsed = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Try to extract [N] prefix
                if line.startswith("["):
                    bracket_end = line.find("]")
                    if bracket_end > 0:
                        try:
                            num = int(line[1:bracket_end])
                            parsed[num] = line[bracket_end + 1:].strip()
                        except ValueError:
                            pass

            # Map back to batch order, falling back to original if parsing fails
            for i, original in enumerate(batch):
                corrected.append(parsed.get(i + 1, original))

        except Exception:
            # On any API error, keep originals
            corrected.extend(batch)

        if progress_callback:
            done = min(batch_start + BATCH_SIZE, len(texts))
            progress_callback(f"LLM correction: {done}/{len(texts)} segments")

    return corrected
