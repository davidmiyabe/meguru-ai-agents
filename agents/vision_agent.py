from langchain_community.chat_models import ChatOpenAI
import os

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("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")
)

def vision_task(destination):
    prompt = f"""
    You are a Meguru vision explorer. List 5 scenic or photo-worthy spots in {destination}.
    Consider light, natural backdrops, and hidden gems.
    """
    return llm.predict(prompt)
