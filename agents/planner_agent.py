from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

def planner_task(filtered_data, dates):
    prompt = f"""
    You are a Meguru itinerary builder. Create a day-by-day itinerary for {dates} based on:
{filtered_data}

    Include buffer time, relaxed mornings, and logical geographical flow.
    """
    return llm.predict(prompt)