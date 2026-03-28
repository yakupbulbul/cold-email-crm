import os
from openai import OpenAI

# Initialize client using the OPENAI_API_KEY environment variable. 
# Defaults to None if not set, requiring setup later.
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    client = None

def summarize_thread(text_content: str) -> str:
    if not client or not text_content:
        return "No content to summarize or API key missing."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes email threads. Provide a concise 2-3 sentence summary."},
            {"role": "user", "content": f"Please summarize this email thread:\n\n{text_content}"}
        ]
    )
    return response.choices[0].message.content

def classify_intent(text_content: str) -> str:
    if not client or not text_content:
        return "Unknown"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that classifies cold email replies into intents. Output ONLY one of these labels: 'Positive Reply', 'Not Interested', 'Question/Objection', 'Out of Office', 'Other'."},
            {"role": "user", "content": f"Classify the intent of this reply:\n\n{text_content}"}
        ]
    )
    return response.choices[0].message.content

def generate_reply(text_content: str, tone: str = "professional") -> str:
    if not client or not text_content:
        return "Cannot generate reply without API key."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"You are a sales assistant writing a {tone} reply to the given email. Be concise and helpful."},
            {"role": "user", "content": f"Write a reply to this email:\n\n{text_content}"}
        ]
    )
    return response.choices[0].message.content
