from app.integrations.openai.provider import OpenAIProvider
from sqlalchemy.orm import Session
from app.models.email import Thread, Message, AiSummary
from fastapi import HTTPException
import json

class AIProcessingService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = OpenAIProvider()
        
    def _get_thread_context(self, thread_id: str) -> str:
        thread = self.db.query(Thread).filter(Thread.id == thread_id).first()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
            
        messages = sorted(thread.messages, key=lambda m: m.created_at)
        context = "\n---\n".join([f"From: {m.from_email}\nText: {m.text_body or m.html_body}" for m in messages])
        return context, thread

    def summarize_thread(self, thread_id: str) -> AiSummary:
        context, thread = self._get_thread_context(thread_id)
        
        prompt = "Summarize the following email thread in two concise sentences."
        summary = self.provider.execute_prompt(prompt, context)
        
        intent_prompt = "Classify the intent of the last email. Options: 'warmup', 'reply', 'interested', 'not_interested', 'meeting_request', 'out_of_office', 'spam', 'support'. Return ONLY the classification word."
        intent = self.provider.execute_prompt(intent_prompt, context).lower().strip()
        
        existing_summary = self.db.query(AiSummary).filter(AiSummary.thread_id == thread_id).first()
        if existing_summary:
            existing_summary.summary = summary
            existing_summary.intent = intent
        else:
            existing_summary = AiSummary(
                thread_id=thread_id,
                summary=summary,
                intent=intent
            )
            self.db.add(existing_summary)
            
        self.db.commit()
        return existing_summary

    def suggest_reply(self, thread_id: str, tone: str = "professional") -> str:
        context, _ = self._get_thread_context(thread_id)
        prompt = f"Draft a concise, {tone} reply to the latest email in this thread. Do not include signature placeholders like [Your Name]. Just the content."
        return self.provider.execute_prompt(prompt, context)
