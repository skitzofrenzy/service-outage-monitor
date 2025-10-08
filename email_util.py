# email_util.py
import os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
FROM_EMAIL = os.getenv('FROM_EMAIL')
TO_EMAILS_ENV = [e.strip() for e in os.getenv('TO_EMAILS','').split(',') if e.strip()]

def send_email_with_attachment(subject, body_html, attachment_path, recipients=None, logger=None):
    to_list = recipients if recipients else TO_EMAILS_ENV
    if not to_list:
        if logger: logger.error("No recipients configured. Set TO_EMAILS or pass recipients.")
        return

    msg = MIMEMultipart()
    msg['From'] = FROM_EMAIL
    msg['To'] = ", ".join(to_list)
    msg['Subject'] = subject
    msg.attach(MIMEText(body_html, 'html'))  # <-- HTML body

    if attachment_path:
        with open(attachment_path, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment_path)}"')
            msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_list, msg.as_string())
            if logger: logger.info(f"Email sent to {', '.join(to_list)} with attachment {attachment_path}")
    except Exception as e:
        if logger: logger.error(f"Failed to send email: {str(e)}")
