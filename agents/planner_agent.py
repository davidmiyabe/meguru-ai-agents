import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def build_itinerary_prompt(filtered_data, dates, preferences):
    return f"""
You are a travel planning agent called Meguru. Your goal is to generate a thoughtful, geographically logical, and personalized day-by-day itinerary for the trip dates: **{dates}**.

### User Preferences
{preferences}

### Contextual Data
Here is the list of locations, activities, and points of interest to consider:
{filtered_data}

---

For **each day**, format your response using the following structure:

- **Breakfast:** Suggest a breakfast spot or meal aligned with preferences.
- **Morning Activity:** Recommend a cultural, relaxing, or inspiring activity nearby that aligns with preferences.
- **Snack (Optional):** Suggest a small local snack or café stop.
- **Lunch:** Recommend a restaurant or food experience that aligns with preferences.
- **Afternoon Activity:** Choose something scenic, creative, or thoughtful that aligns with preferences.
- **Snack (Optional):** Include only if the day’s pace benefits from it.
- **Dinner:** Curated dinner spot or culinary experience that that aligns with preferences.
- **After-Dinner Activity (Optional):** Suggestions for evenings that aligns with preferences.

Use logical flow, avoid backtracking between neighborhoods, and include buffer time between activities. You may vary the pace across days — not every day has to be packed.

Respond in markdown format with headings for each day.
"""

def planner_task(filtered_data, dates, preferences):
    prompt = build_itinerary_prompt(filtered_data, dates, preferences)
    return llm.predict(prompt)
