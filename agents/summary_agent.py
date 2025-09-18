from langchain_community.chat_models import ChatOpenAI
import os

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("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")
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
