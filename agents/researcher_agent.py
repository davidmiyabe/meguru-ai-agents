from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")

def researcher_task(destination, dates):
    prompt = f"""
    You are a travel researcher. List top 3 Meguru-style boutique stays, 3 must-visit nature spots,
    and 3 hidden food gems and local tea houses in {destination} between {dates}.
    No tourist traps. Prioritize beauty, walkability, and tea culture.
    """
    return llm.predict(prompt)
