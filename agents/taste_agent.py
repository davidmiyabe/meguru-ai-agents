from langchain_community.chat_models import ChatOpenAI
import os

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("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")
)

def taste_task(raw_data, preferences):
    prompt = f"""
    You are a taste agent. Given the following travel data:
{raw_data}

    Filter it based on the user's preferences: {preferences}
    Prioritize emotional fit, uniqueness, and visual/aesthetic appeal.
    """
    return llm.predict(prompt)
