import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def build_taste_prompt(raw_data, preferences):
    return f"""
You are a Meguru **Taste Agent** responsible for curating food-related experiences.

Given the following travel data:
---
{raw_data}
---

Filter and elevate the **food and drink** recommendations using these criteria:
- Match the user's **vibe/preferences**: *{preferences}*
- Prioritize **unique, high-quality, and local** culinary experiences
- Highlight any options with strong **visual appeal** (e.g., beautifully plated, ambient settings)
- Include a variety across the
