import imaplib
from typing import List, Tuple

class MailcowIMAPProvider:
    def fetch_unread_messages(self, host, port, username, password) -> List[Tuple[str, bytes]]:
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(username, password)
            mail.select("inbox")
            
            _, messages = mail.search(None, "UNSEEN")
            if not messages[0]:
                return []
                
            email_ids = messages[0].split()
            raw_emails = []
            
            for e_id in email_ids:
                _, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw_emails.append((e_id.decode(), response_part[1]))
            
            mail.logout()
            return raw_emails
        except Exception:
            return []
            
    def mark_as_read(self, host, port, username, password, email_id: str):
        try:
            mail = imaplib.IMAP4_SSL(host, port)
            mail.login(username, password)
            mail.select("inbox")
            mail.store(email_id, '+FLAGS', '\\Seen')
            mail.logout()
        except Exception:
            pass
