from langchain_community.chat_models import ChatOpenAI
import os

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("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")
)

def researcher_task(destination, dates):
    prompt = f"""
    You are a travel researcher. List top 3 Meguru-style boutique stays, 3 must-visit nature spots,
    and 3 hidden food gems and local tea houses in {destination} between {dates}.
    No tourist traps. Prioritize beauty, walkability, and tea culture.
    """
    return llm.predict(prompt)
