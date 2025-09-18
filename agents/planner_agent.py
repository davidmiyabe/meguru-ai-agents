from langchain_community.chat_models import ChatOpenAI
import os

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("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")
)

def planner_task(filtered_data, dates):
    prompt = f"""
    You are a Meguru itinerary builder. Create a day-by-day itinerary for {dates} based on:
{filtered_data}

    Include buffer time, relaxed mornings, and logical geographical flow.
    """
    return llm.predict(prompt)
