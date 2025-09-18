import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def build_summary_prompt(calendar, photo_spots):
    return f"""
You are a **Meguru Trip Summarizer**.

Your goal is to create a **cinematic, emotionally resonant, and well-formatted summary** of the following trip:

---

**📅 Itinerary:**
{calendar}

---

**📸 Scenic Photo Spots:**
{photo_spots}

---

**Output Instructions:**
- Write a day-by-day summary in **Markdown** with headings for each day (e.g. `### Day 1: Arrival in Kyoto`)
- Keep the tone **peaceful, poetic, and inspiring**
- Add light transitions between morning → afternoon → evening
- Include references to the **photo spots** when relevant to enhance the storytelling
- Close with a brief reflection on the overall trip mood or intention

Your output should feel like a memory—inviting, vivid, and gentle.
"""

def summary_task(calendar, p_
