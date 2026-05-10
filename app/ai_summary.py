import os

HF_BASE_URL = "https://router.huggingface.co/v1"
HF_MODEL = "moonshotai/Kimi-K2-Instruct-0905"


class SummarizationConfigError(RuntimeError):
    """Raised when the Hugging Face summarization client is not configured."""


class SummarizationError(RuntimeError):
    """Raised when the summarization request fails."""


def generate_summary(text: str) -> str:
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise SummarizationConfigError(
            "HF_TOKEN is not set. Add it to .env before using AI summarization."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SummarizationConfigError(
            "The openai package is not installed. Install project dependencies before using AI summarization."
        ) from exc

    client = OpenAI(base_url=HF_BASE_URL, api_key=hf_token)

    try:
        completion = client.chat.completions.create(
            model=HF_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise summarization assistant. "
                        "Summarize clearly, keep the main points, and avoid filler."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Summarize the following text in a concise way. "
                        "Use a short paragraph followed by 3 to 5 bullet points when helpful.\n\n"
                        + text.strip()
                    ),
                },
            ],
        )
    except Exception as exc:
        raise SummarizationError("The Hugging Face summarization request failed.") from exc

    message = completion.choices[0].message.content if completion.choices else None
    if not message:
        raise SummarizationError("The summarization model returned an empty response.")

    return message.strip()
