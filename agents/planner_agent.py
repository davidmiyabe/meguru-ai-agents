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

    Include buffer time, relaxed mornings, and logical geographical flow.
    """
    return llm.predict(prompt)
