import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")  # This is the name of your secret
)

def summary_task(calendar, photo_spots):
    prompt = f"""
    You are a trip summarizer. Using the following itinerary:
{calendar}

    And scenic spots:
{photo_spots}

    Generate a beautifully formatted day-by-day trip summary.
    """
    return llm.predict(prompt)
