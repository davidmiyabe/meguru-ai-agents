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

Summarize the trip, day by day, as if writing for a luxury travel magazine. Highlight the why, scenic flow, and meaningful moments using the following structure:

- **Breakfast:** Suggest a breakfast spot or meal aligned with preferences.
- **Morning Activity:** Recommend a cultural, relaxing, or inspiring activity nearby that aligns with preferences.
- **Snack (Optional):** Suggest a small local snack or café stop.
- **Lunch:** Recommend a restaurant or food experience that aligns with preferences.
- **Afternoon Activity:** Choose something scenic, creative, or thoughtful that aligns with preferences.
- **Snack (Optional):** Include only if the day’s pace benefits from it.
- **Dinner:** Curated dinner spot or culinary experience that that aligns with preferences.
- **After-Dinner Activity (Optional):** Suggestions for evenings that aligns with preferences.



Use elegant, engaging, and inspiring language. Format it cleanly in Markdown.
"""
    return llm.predict(prompt)
