from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

def summary_task(calendar, photo_spots):
    prompt = f"""
    You are a trip summarizer. Using the following itinerary:
{calendar}

    And scenic spots:
{photo_spots}

    Generate a beautifully formatted day-by-day trip summary.
    """
    return llm.predict(prompt)
