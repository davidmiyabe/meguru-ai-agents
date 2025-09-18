import os
from langchain_community.chat_models import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

def build_vision_prompt(destination, preferences=None):
    base_prompt = f"""
You are a vision agent for the Meguru AI travel planner.

Suggest **5 scenic, photo-worthy locations** in or around **{destination}**.

Each location should:
- Be visually stunning or unique (great for photography)
- Include a short 1–2 sentence explanation of why it’s photogenic
- Include the type of photo it lends itself to (e.g. wide landscape, close-up, sunset shot)
- Include whether it’s a popular landmark or a hidden gem

"""
    if preferences:
        base_prompt += f"""Prioritize locations that match the user’s vibe or preferences: **{preferences}**.\n"""
    base_prompt += "Respond as a clean markdown list with bold location names."

    return base_prompt.strip()

def vision_task(destination, preferences=None):
    prompt = build_vision_prompt(destination, preferences)
    return llm.predict(prompt)
