import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def summary_task(calendar, photo_spots):
    prompt = f"""
You are a **Trip Summarizer** for a high-end AI travel companion.

---

**Itinerary**:
{calendar}

---

**Scenic Photo Spots**:
{photo_spots}

---

Summarize the trip beautifully, day by day, as if writing for a luxury travel magazine. Highlight the emotional tone, scenic flow, and meaningful moments.

Use elegant, engaging, and inspiring language. Format it cleanly in Markdown.
"""
    return llm.predict(prompt)
