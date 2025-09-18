from agents.researcher_agent import researcher_task
from agents.taste_agent import taste_task
from agents.planner_agent import planner_task
from agents.vision_agent import vision_task
from agents.summary_agent import summary_task

def run_trip_pipeline(destination, dates, preferences):
    raw_data = researcher_task(destination, dates, preferences)
    filtered_data = taste_task(raw_data, preferences)
    calendar = planner_task(filtered_data, dates)
    scenic_spots = vision_task(destination)
    summary = summary_task(calendar, scenic_spots)
    return summary
