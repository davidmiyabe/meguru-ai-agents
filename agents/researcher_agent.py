import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def researcher_task(destination, dates, preferences):
    prompt = f"""
You are a **Meguru Travel Researcher**. Your role is to curate meaningful and visually stunning experiences based on the user's travel style.

---

**Trip Details**
- Destination: {destination}
- Dates: {dates}
- Traveler Preferences: {preferences}

---

**Output Instructions**
Curate the following, avoiding cliché tourist traps:

1. **Top 3 Lodging Options**
   - Unique, beautiful, and emotionally aligned with preferences  
   - Include name, neighborhood, and a 1-line poetic reason why it's special

2. **10 Must-Visit Spots**
   - Mix of natural, cultural, and historic experiences
   - Include a 1-sentence vibe match for each one

3. **10 Hidden Gems**
   - Lesser-known places: secret gardens, tucked-away tea houses, sunset spots
   - Prioritize uniqueness and originality
   - Each should include a sensory detail or emotional appeal

---

Tone: Warm, intentional, cinematic.
Focus: Emotional fit, aesthetic appeal, slow discovery.
"""
    return llm.predict(prompt)
