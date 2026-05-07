__all__ = [
    "send_verification_email",
    "EmailSendError",
]

import base64
import resend
from datetime import datetime
from os import getenv
from pathlib import Path
from typing import Optional, Union
from flask import current_app, render_template
from resend import Tag, Attachment, RemoteAttachment
from app.core.logging import get_logger

logger = get_logger()

RESEND_API_KEY = getenv("RESEND_API_KEY")

BRAND_NAME = "Drssed"
DEFAULT_FROM_ADDRESS = getenv("EMAIL_FROM_ADDRESS", "noreply@drssed.app")
DEFAULT_REPLY_TO = getenv("EMAIL_REPLY_TO", "support@drssed.app")
EMAIL_ENABLED = getenv("EMAIL_ENABLED", "true").lower() == "true"

SUPPORTED_LOCALES = {"en", "de"}
DEFAULT_LOCALE = "en"

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
    text: str,
    from_address: Optional[str] = None,
    reply_to: Optional[str] = None,
    tags: Optional[list[Tag]] = None,
    attachments: Optional[list[Attachment | RemoteAttachment]] = None,
    headers: Optional[dict[str, str]] = None,
) -> Optional[str]:
    """
    Send a transactional email via Resend.
    
    Both `html` and `text` are required: the multipart/alternative format is 
    standard for transactional emails and reduces spam-filter penalties, plus 
    plain-text serves as an accessibility fallback.
    
    :param to: Single recipient or list of recipients.
    :param subject: Email subject line.
    :param html: HTML body of the email.
    :param text: Plain-text body of the email.
    :param from_address: Optional sender. Defaults to DEFAULT_FROM_ADDRESS.
    :param reply_to: Optional reply-to. Defaults to DEFAULT_REPLY_TO.
    :param tags: Optional Resend tags for dashboard categorization.
    :param attachments: Optional list of Resend attachment dicts (filename, 
                        content as base64, content_id, disposition).
    :param headers: Optional custom email headers.
    :return: Resend email ID on success, None if email sending is disabled.
    :raises EmailSendError: If sending fails.
    """
    if not EMAIL_ENABLED:
        logger.debug(
            "Email sending is disabled. Skipping email.",
            extra={"to": to, "subject": subject},
        )
        return None
    
    recipients = [to] if isinstance(to, str) else to
    sender_address = from_address or DEFAULT_FROM_ADDRESS
    
    params: resend.Emails.SendParams = {
        "from": f"{BRAND_NAME} <{sender_address}>",
        "to": recipients,
        "subject": subject,
        "html": html,
        "text": text,
        "reply_to": reply_to or DEFAULT_REPLY_TO,
    }
    
    if tags:
        params["tags"] = tags
    
    if attachments:
        params["attachments"] = attachments
    
    if headers:
        params["headers"] = headers
    
    try:
        response = resend.Emails.send(params)
        email_id = response.get("id") if isinstance(response, dict) else None
        
        logger.debug("Email sent successfully",
            extra={
                "to": recipients,
                "subject": subject,
                "resend_id": email_id,
                "has_attachments": bool(attachments),
            },
        )
        
        return email_id
    
    except Exception as e:
        logger.error(
            "Failed to send email",
            extra={
                "to": recipients,
                "subject": subject,
                "error": str(e),
            },
        )
        raise EmailSendError() from e

def send_verification_email(
    user_email: str,
    locale: str,
    verification_link: str,
    expiry_hours: int,
) -> Optional[str]:
    """
    Send an email-verification email with the brand logo as inline attachment.
    
    Renders the HTML and plain-text templates for the given locale, falling 
    back to DEFAULT_LOCALE if locale is unsupported.
    
    :param user_email: Recipient's email address.
    :param locale: Target locale ('en' or 'de'). Falls back to default if unsupported.
    :param verification_link: The full URL the user should click to verify.
    :param expiry_hours: How many hours until the verification link expires.
    :param user_name: Optional user name for personalized greeting.
    :return: Resend email ID on success, None if email sending is disabled.
    :raises EmailSendError: If sending fails.
    """
    resolved_locale = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    
    template_vars = {
        "verification_link": verification_link,
        "expiry_hours": expiry_hours,
        "current_year": datetime.now().year,
        "lang": resolved_locale,
    }
    
    html = render_template(
        f"/verification/verification.{resolved_locale}.html",
        **template_vars,
    )
    text = render_template(
        f"/verification/verification.{resolved_locale}.txt",
        **template_vars,
    )
    
    subject = render_template(
        f"/verification/subject.{locale}.txt",
        **template_vars,
    ).strip()
    
    return send_email(
        to=user_email,
        subject=subject,
        html=html,
        text=text,
        attachments=[],
        tags=[{"name": "category", "value": "verification"}],
    )

def _build_logo_attachment() -> Attachment:
    """
    Load the Drssed logo from static/emails/logo.png and return a 
    Resend-compatible inline attachment dict.
    
    The content_id "logo" matches the cid:logo reference in HTML templates.
    """
    logo_path = _get_static_folder() / "emails" / "logo.png"
    
    with open(logo_path, "rb") as f:
        logo_bytes = f.read()
    
    return {
        "filename": "logo.png",
        "content": base64.b64encode(logo_bytes).decode(),
        "content_id": "logo"
    }

def _get_static_folder() -> Path:
    folder = current_app.static_folder
    
    if not folder:
        raise RuntimeError("⚠️ Flask static_folder is not configured")
    
    return Path(folder)

def _get_templates_folder() -> str:
    folder = current_app.template_folder
    
    if not folder:
        raise RuntimeError("⚠️ Flask template_folder is not configured")
    
    return str(folder)