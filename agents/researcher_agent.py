import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")  # This is the name of your secret
)

def researcher_task(destination, dates):
    prompt = f"""
    You are a travel researcher. List top 3 stays, 10 must-visit spots based on the user's preferences: {preferences},
    and 10 hidden food gems in {destination} between {dates}.
    No tourist traps. Prioritize based on the user's preferences: {preferences} prioritize emotional fit, uniqueness, and visual/aesthetic appeal
    """
    return llm.predict(prompt)
