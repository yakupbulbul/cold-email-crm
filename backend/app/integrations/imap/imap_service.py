import imaplib
import email
from email.header import decode_header
from app.models.models import Mailbox
import traceback

def fetch_unread_emails(mailbox: Mailbox):
    emails_data = []
    try:
        # Connect to Mailcow IMAP
        # Note: Depending on server config, port 143 might require starttls, 
        # or port 993 requires IMAP4_SSL. We attempt SSL on 993 as typical fallback.
        if mailbox.imap_port == 993:
            imap = imaplib.IMAP4_SSL(mailbox.imap_host, mailbox.imap_port)
        else:
            imap = imaplib.IMAP4(mailbox.imap_host, mailbox.imap_port)
            imap.starttls()

        imap.login(mailbox.email, mailbox.password)
        imap.select("INBOX")
        
        status, messages = imap.search(None, 'UNSEEN')
        if status == "OK" and messages[0]:
            for num in messages[0].split():
                res, msg_data = imap.fetch(num, '(RFC822)')
                if res == "OK":
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            subject, encoding = decode_header(msg.get("Subject", ""))[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else 'utf-8', errors="ignore")
                            else:
                                subject = str(subject)
                            
                            from_ = msg.get("From")
                            message_id = msg.get("Message-ID")
                            in_reply_to = msg.get("In-Reply-To")
                            
                            text_content = ""
                            html_content = ""
                            
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    if content_type == "text/plain":
                                        try:
                                            text_content += part.get_payload(decode=True).decode(errors="ignore")
                                        except:
                                            pass
                                    elif content_type == "text/html":
                                        try:
                                            html_content += part.get_payload(decode=True).decode(errors="ignore")
                                        except:
                                            pass
                            else:
                                content_type = msg.get_content_type()
                                if content_type == "text/plain":
                                    text_content = msg.get_payload(decode=True).decode(errors="ignore")
                                elif content_type == "text/html":
                                    html_content = msg.get_payload(decode=True).decode(errors="ignore")
                                    
                            emails_data.append({
                                "subject": subject,
                                "from": from_,
                                "message_id": message_id,
                                "in_reply_to": in_reply_to,
                                "text_content": text_content,
                                "html_content": html_content
                            })
        imap.close()
        imap.logout()
    except Exception as e:
        print(f"Error fetching IMAP for {mailbox.email}: {e}")
        traceback.print_exc()
        
    return emails_data
