import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")  # This is the name of your secret
)

def vision_task(destination):
    prompt = f"""
    You are a Meguru vision explorer. List 5 scenic or photo-worthy spots in {destination}.
    Consider light, natural backdrops, and hidden gems.
    """
    return llm.predict(prompt)
