import smtplib
import socks
from email.message import EmailMessage
from typing import List, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class SMTPProvider(ABC):
    @abstractmethod
    def send_email(self, 
                   host: str, 
                   port: int, 
                   username: str, 
                   password: str, 
                   from_email: str, 
                   to_emails: List[str], 
                   subject: str, 
                   text_body: str, 
                   html_body: Optional[str] = None,
                   cc_emails: Optional[List[str]] = None,
                   bcc_emails: Optional[List[str]] = None,
                   in_reply_to: Optional[str] = None,
                   references: Optional[str] = None) -> tuple[bool, str]:
        pass

class MailcowSMTPProvider(SMTPProvider):
    def send_email(self, 
                   host: str, 
                   port: int, 
                   username: str, 
                   password: str, 
                   from_email: str, 
                   to_emails: List[str], 
                   subject: str, 
                   text_body: str, 
                   html_body: Optional[str] = None,
                   cc_emails: Optional[List[str]] = None,
                   bcc_emails: Optional[List[str]] = None,
                   in_reply_to: Optional[str] = None,
                   references: Optional[str] = None) -> tuple[bool, str]:
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ", ".join(to_emails)
        
        if cc_emails:
            msg['Cc'] = ", ".join(cc_emails)
            
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references
            
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype='html')
            
        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.login(username, password)
                
                # Combine all recipients for the RCPT TO envelope
                all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])
                server.send_message(msg, from_addr=from_email, to_addrs=all_recipients)
                message_id = msg.get('Message-ID', 'unknown-id')
                return True, message_id
                
        except Exception as e:
            logger.error(f"SMTP Error: {str(e)}")
            return False, str(e)
