from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

def taste_task(raw_data, preferences):
    prompt = f"""
    You are a taste agent. Given the following travel data:
{raw_data}

    Filter it based on the user's preferences: {preferences}
    Prioritize emotional fit, uniqueness, and visual/aesthetic appeal.
    """
    return llm.predict(prompt)
