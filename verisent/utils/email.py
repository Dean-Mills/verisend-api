"""
Email service for sending transactional emails via SMTP (Brevo).
"""

import logging

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from verisent.settings import settings

logger = logging.getLogger(__name__)


async def send_magic_link_email(to_email: str, magic_link: str) -> None:
    """Send magic link email"""
    message = MIMEMultipart("alternative")
    message["Subject"] = "Login to Zylentra"
    message["From"] = f"Zylentra <{settings.smtp_from}>"
    message["To"] = to_email

    text = f"""
Hi,

Click the link below to login:

{magic_link}

This link expires in 15 minutes.

If you didn't request this, ignore this email.
    """

    html = f"""
<html>
  <body>
    <h2>Login to Zylentra</h2>
    <p>Click the button below to login:</p>
    <p>
      <a href="{magic_link}"
         style="background-color: #0066cc; color: white; padding: 12px 24px;
                text-decoration: none; border-radius: 4px; display: inline-block;">
        Login Now
      </a>
    </p>
    <p>Or copy this link: <br><code>{magic_link}</code></p>
    <p style="color: #666; font-size: 12px;">
      This link expires in 15 minutes.
    </p>
  </body>
</html>
    """

    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password.get_secret_value(),
        start_tls=True,
    )


async def send_form_assignment_email(
    to_email: str,
    form_name: str,
    org_name: str | None = None,
) -> None:
    """Notify a user that a form has been assigned to them."""
    sender = org_name or "Verisent"
    message = MIMEMultipart("alternative")
    message["Subject"] = f"{sender} has assigned you a form: {form_name}"
    message["From"] = f"Verisent <{settings.smtp_from}>"
    message["To"] = to_email

    text = f"""
Hi,

{sender} has assigned you a form to complete: "{form_name}".

To fill it in, please visit the Verisent website and sign in with this email address. You'll find the form waiting for you on your dashboard.

If you don't have an account yet, you'll be prompted to create one using this email address.
    """

    html = f"""
<html>
  <body>
    <h2>You've been assigned a form</h2>
    <p><strong>{sender}</strong> has assigned you a form to complete: <strong>{form_name}</strong>.</p>
    <p>To fill it in, please visit the Verisent website and sign in with this email address. You'll find the form waiting for you on your dashboard.</p>
    <p style="color: #666; font-size: 12px;">
      If you don't have an account yet, you'll be prompted to create one using this email address.
    </p>
  </body>
</html>
    """

    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password.get_secret_value(),
        start_tls=True,
    )
