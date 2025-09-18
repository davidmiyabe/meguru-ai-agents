import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)


def summary_task(calendar, photo_spots, preferences):
    prompt = f"""
You are a **Trip Summarizer** for a high-end AI travel companion.

---

**Itinerary**:
{calendar}

---

**Scenic Photo Spots**:
{photo_spots}

---

**Traveler Vibe & Preferences**:
{preferences}

---

Summarize the trip, day by day, as if writing for a luxury travel magazine. Highlight the why, scenic flow, and meaningful moments using the following structure:

- **Breakfast:** Suggest a breakfast spot or meal that fits the traveler vibe ({preferences}).
- **Morning Activity:** Recommend a cultural, relaxing, or inspiring activity nearby that reflects the traveler vibe ({preferences}).
- **Snack (Optional):** Suggest a small local snack or café stop that complements the vibe ({preferences}).
- **Lunch:** Recommend a restaurant or food experience in tune with the vibe ({preferences}).
- **Afternoon Activity:** Choose something scenic, creative, or thoughtful that resonates with the vibe ({preferences}).
- **Snack (Optional):** Include only if the day’s pace benefits from it and it enhances the vibe ({preferences}).
- **Dinner:** Curated dinner spot or culinary experience that matches the vibe ({preferences}).
- **After-Dinner Activity (Optional):** Suggest evenings that stay true to the vibe ({preferences}).



Use elegant, engaging, and inspiring language. Format it cleanly in Markdown.
"""
    return llm.predict(prompt)
