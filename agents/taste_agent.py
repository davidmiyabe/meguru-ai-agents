import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def taste_task(raw_data, preferences):
    prompt = f"""
You are a **Taste Agent** for a travel planning AI. Your job is to curate meaningful, personalized, ideal, beautiful, and delicious experiences for travelers.

---

**Traveler Preferences**: {preferences}

**Raw Travel Data**:
{raw_data}

---

Filter and enhance the above data to include:
- Unique and visually striking food/drink stops
- Culturally rich or emotionally resonant experiences
- Local flavors and specialty dishes
- Any recommended snack stops or desserts that align with the vibe

Prioritize storytelling, uniqueness, and emotional fit.
Output in Markdown format.
"""
    return llm.predict(prompt)
