"""
Email service — sends SMTP email notifications for platform events.

Uses Python's built-in smtplib and email.mime modules (no external deps).
Controlled by SMTP_* environment variables via app.core.config.settings.
All public functions are safe to call unconditionally — they never raise.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status label mappings (Arabic)
# ---------------------------------------------------------------------------

COMPLAINT_STATUS_LABELS: Dict[str, str] = {
    "new": "جديدة",
    "under_review": "قيد المراجعة",
    "assigned": "تم التعيين",
    "in_progress": "قيد التنفيذ",
    "resolved": "تم الحل",
    "rejected": "مرفوضة",
}

CONTRACT_ACTION_LABELS: Dict[str, str] = {
    "approve": "تمت الموافقة",
    "activate": "تم التفعيل",
    "complete": "تم الإنجاز",
    "suspend": "تم التعليق",
    "cancel": "تم الإلغاء",
}

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_BASE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    margin: 0; padding: 0;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    background-color: #f4f6f8;
    direction: rtl;
  }}
  .container {{
    max-width: 560px;
    margin: 32px auto;
    background: #ffffff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }}
  .header {{
    background-color: #1a56db;
    color: #ffffff;
    padding: 20px 24px;
    font-size: 18px;
    font-weight: 600;
  }}
  .body {{
    padding: 24px;
    color: #1f2937;
    font-size: 15px;
    line-height: 1.7;
  }}
  .label {{
    color: #6b7280;
    font-size: 13px;
  }}
  .value {{
    font-weight: 600;
  }}
  .footer {{
    text-align: center;
    padding: 16px 24px;
    font-size: 12px;
    color: #9ca3af;
    border-top: 1px solid #e5e7eb;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">{title}</div>
  <div class="body">{content}</div>
  <div class="footer">منصة إدارة مشروع دمّر</div>
</div>
</body>
</html>
"""


def _render_html(title: str, content: str) -> str:
    """Render *content* inside the base HTML email template."""
    return _BASE_TEMPLATE.format(title=title, content=content)


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------


def send_email(to_email: str, subject: str, body_html: str) -> None:
    """Send an HTML email via SMTP.

    * Returns immediately (no-op) when ``SMTP_ENABLED`` is ``False``.
    * Never raises — all exceptions are caught and logged.
    """
    if not settings.SMTP_ENABLED:
        logger.debug(
            "SMTP disabled — skipping email to %s (subject: %s)", to_email, subject
        )
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info("Email sent successfully to %s (subject: %s)", to_email, subject)

    except Exception:
        logger.exception(
            "Failed to send email to %s (subject: %s)", to_email, subject
        )


# ---------------------------------------------------------------------------
# Notification-specific helpers
# ---------------------------------------------------------------------------


def send_complaint_status_email(
    to_email: str,
    tracking_number: str,
    old_status: str,
    new_status: str,
) -> None:
    """Notify a user that their complaint status has changed."""
    try:
        old_label = COMPLAINT_STATUS_LABELS.get(old_status, old_status)
        new_label = COMPLAINT_STATUS_LABELS.get(new_status, new_status)

        content = (
            "<p>تم تحديث حالة الشكوى الخاصة بك.</p>"
            "<p>"
            f'<span class="label">رقم التتبع:</span> '
            f'<span class="value">{tracking_number}</span><br>'
            f'<span class="label">الحالة السابقة:</span> '
            f'<span class="value">{old_label}</span><br>'
            f'<span class="label">الحالة الجديدة:</span> '
            f'<span class="value">{new_label}</span>'
            "</p>"
        )

        html = _render_html("تحديث حالة الشكوى", content)
        send_email(to_email, "تحديث حالة الشكوى", html)

    except Exception:
        logger.exception(
            "Error preparing complaint status email for %s (tracking: %s)",
            to_email,
            tracking_number,
        )


def send_task_assignment_email(
    to_email: str,
    task_title: str,
    assignee_name: str,
) -> None:
    """Notify a user that a task has been assigned to them."""
    try:
        content = (
            "<p>تم تعيين مهمة جديدة لك.</p>"
            "<p>"
            f'<span class="label">عنوان المهمة:</span> '
            f'<span class="value">{task_title}</span><br>'
            f'<span class="label">المكلّف:</span> '
            f'<span class="value">{assignee_name}</span>'
            "</p>"
        )

        html = _render_html("تعيين مهمة جديدة", content)
        send_email(to_email, "تعيين مهمة جديدة", html)

    except Exception:
        logger.exception(
            "Error preparing task assignment email for %s (task: %s)",
            to_email,
            task_title,
        )


def send_contract_status_email(
    to_email: str,
    contract_number: str,
    action: str,
) -> None:
    """Notify a user about a contract status change."""
    try:
        action_label = CONTRACT_ACTION_LABELS.get(action, action)

        content = (
            "<p>تم تحديث حالة العقد.</p>"
            "<p>"
            f'<span class="label">رقم العقد:</span> '
            f'<span class="value">{contract_number}</span><br>'
            f'<span class="label">الإجراء:</span> '
            f'<span class="value">{action_label}</span>'
            "</p>"
        )

        html = _render_html("تحديث حالة العقد", content)
        send_email(to_email, "تحديث حالة العقد", html)

    except Exception:
        logger.exception(
            "Error preparing contract status email for %s (contract: %s)",
            to_email,
            contract_number,
        )
