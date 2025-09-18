import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")  # This is the name of your secret
)

def planner_task(filtered_data, dates):
    prompt = f"""
    You are a Meguru itinerary builder. Create a day-by-day itinerary for {dates} based on:
{filtered_data}

    Please format each day with the following structure:
- **Breakfast:** A recommended breakfast spot or type of meal that fits the user's preferences: {preferences}
- **Morning Activity:** An ideal activity based on the user's preferences: {preferences} and the rest of the itinerary
- **Snack:** Optional rcommended snack that fits the user's preferences: {preferences} and the rest of the itinerary
- **Lunch:** A restaurant recommendation or type of meal that fits the user's preferences: {preferences}
- **Afternoon Activity:** An ideal activity based on the user's preferences: {preferences} and the rest of the itinerary
- **Snack:** Optional rcommended snack that fits the user's preferences: {preferences} and the rest of the itinerary
- **Dinner:** A curated dinner spot or meaningful food experiencethat fits the user's preferences: {preferences}
- **After-Dinner Activity:** Optional based on the user's preferences: {preferences} and the rest of the itinerary

    Include buffer time, base reccomedations on the user's preferences: {preferences}, and logical geographical flow.
    """
    return llm.predict(prompt)
