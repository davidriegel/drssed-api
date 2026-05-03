__all__ = ["send_email", "EmailSendError"]

import resend
from resend import Tag
from os import getenv
from typing import Optional, Union
from app.core.logging import get_logger

logger = get_logger()

RESEND_API_KEY = getenv("RESEND_API_KEY")

BRAND_NAME = "Drssed"
DEFAULT_FROM_ADDRESS = getenv("EMAIL_FROM_ADDRESS", "noreply@drssed.app")
DEFAULT_REPLY_TO = getenv("EMAIL_REPLY_TO", "support@drssed.app")
EMAIL_ENABLED = getenv("EMAIL_ENABLED", "true").lower() == "true"

if EMAIL_ENABLED and not RESEND_API_KEY:
    raise RuntimeError("⚠️ RESEND_API_KEY must be set when EMAIL_ENABLED is true")

if EMAIL_ENABLED:
    resend.api_key = RESEND_API_KEY


class EmailSendError(Exception):
    """Raised when an email fails to send."""
    pass

def send_email(
    to: Union[str, list[str]],
    subject: str,
    html: str,
    from_address: Optional[str] = None,
    reply_to: Optional[str] = None,
    tags: Optional[list[Tag]] = None,
) -> Optional[str]:
    """
    Send a transactional email.
    
    :param from_address: Optional sender email address. Defaults to DEFAULT_FROM_ADDRESS.
    """
    if not EMAIL_ENABLED:
        logger.debug(f"Email sending is disabled. Skipping email to {to} with subject '{subject}'.")
        return None
    
    recipients = [to] if isinstance(to, str) else to
    sender_address = from_address or DEFAULT_FROM_ADDRESS
    
    params: resend.Emails.SendParams = {
        "from": f"{BRAND_NAME} <{sender_address}>",
        "to": recipients,
        "subject": subject,
        "html": html,
        "reply_to": reply_to or DEFAULT_REPLY_TO,
    }
    
    if tags:
        params["tags"] = tags
    
    try:
        response = resend.Emails.send(params)
        email_id = response.get("id") if isinstance(response, dict) else None
        
        logger.debug("Email sent successfully", extra={"to": recipients, "subject": subject, "resend_id": email_id})
        
        return email_id
    
    except Exception as e:
        logger.error("Failed to send email", extra={"to": recipients, "subject": subject, "error": str(e)})
        raise EmailSendError() from e