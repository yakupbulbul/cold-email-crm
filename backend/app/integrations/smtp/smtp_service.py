import smtplib
from email.message import EmailMessage
from app.models.models import Mailbox

def send_email(mailbox: Mailbox, to_email: str, subject: str, html_content: str, text_content: str = None, in_reply_to: str = None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mailbox.email
    msg['To'] = to_email

    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
        msg['References'] = in_reply_to

    if html_content and text_content:
        msg.set_content(text_content)
        msg.add_alternative(html_content, subtype='html')
    elif html_content:
        msg.set_content(html_content, subtype='html')
    else:
        msg.set_content(text_content or "")

    # Connect to Mailcow SMTP
    with smtplib.SMTP(mailbox.smtp_host, mailbox.smtp_port) as server:
        server.starttls()
        server.login(mailbox.email, mailbox.password)
        server.send_message(msg)
    
    return True
