import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")  # This is the name of your secret
)

def taste_task(raw_data, preferences):
    prompt = f"""
    You are a taste agent. Given the following travel data:
{raw_data}

    Filter it based on the user's preferences: {preferences}
    Prioritize emotional fit, uniqueness, and visual/aesthetic appeal.
    """
    return llm.predict(prompt)
