"""Email service for sending notifications."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self):
        """Initialize email service with SMTP configuration."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.email_from or settings.smtp_user

    def _validate_config(self) -> bool:
        """Validate email configuration."""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning("Email service not configured properly")
            return False
        return True

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (fallback)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._validate_config():
            logger.error("Cannot send email - configuration invalid")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Add text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, "plain")
                msg.attach(part1)

            part2 = MIMEText(html_content, "html")
            msg.attach(part2)

            # Send email
            logger.info(f"Sending email to {to_email} with subject: {subject}")

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP authentication failed: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error sending email: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {str(e)}")
            return False

    def send_task_reminder(
        self,
        to_email: str,
        username: str,
        expiring_tasks: list[dict[str, Any]],
        pending_tasks: list[dict[str, Any]],
    ) -> bool:
        """Send task reminder email.

        Args:
            to_email: Recipient email address
            username: User's name
            expiring_tasks: List of tasks expiring soon
            pending_tasks: List of pending tasks

        Returns:
            True if email sent successfully, False otherwise
        """
        # Generate HTML content
        html_content = self._generate_reminder_html(
            username, expiring_tasks, pending_tasks
        )

        # Generate plain text content
        text_content = self._generate_reminder_text(
            username, expiring_tasks, pending_tasks
        )

        subject = "📋 Your Daily Task Reminder"

        return self.send_email(to_email, subject, html_content, text_content)

    def _generate_reminder_html(
        self,
        username: str,
        expiring_tasks: list[dict[str, Any]],
        pending_tasks: list[dict[str, Any]],
    ) -> str:
        """Generate HTML content for task reminder email."""
        expiring_html = ""
        if expiring_tasks:
            expiring_html = """
            <div style="margin-bottom: 30px;">
                <h2 style="color: #dc2626; margin-bottom: 15px;">⏰ Tasks Expiring Soon</h2>
                <div style="background-color: #fef2f2; padding: 15px; border-radius: 8px; border-left: 4px solid #dc2626;">
            """
            for task in expiring_tasks:
                priority_color = self._get_priority_color(task.get("priority", 3))
                expiring_html += f"""
                    <div style="margin-bottom: 15px; padding: 10px; background-color: white; border-radius: 6px;">
                        <div style="display: flex; align-items: center; margin-bottom: 5px;">
                            <span style="background-color: {priority_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">
                                {self._get_priority_label(task.get("priority", 3))}
                            </span>
                            <strong style="color: #1f2937;">{task.get("title", "Untitled Task")}</strong>
                        </div>
                        <p style="color: #6b7280; margin: 5px 0; font-size: 14px;">{task.get("description", "No description") if task.get("description") else "No description"}</p>
                        <p style="color: #dc2626; font-weight: 500; font-size: 13px; margin: 5px 0;">
                            📅 Due: {task.get("due_date", "Not set")}
                        </p>
                    </div>
                """
            expiring_html += """
                </div>
            </div>
            """

        pending_html = ""
        if pending_tasks:
            pending_html = """
            <div style="margin-bottom: 30px;">
                <h2 style="color: #2563eb; margin-bottom: 15px;">📝 Pending Tasks</h2>
                <div style="background-color: #eff6ff; padding: 15px; border-radius: 8px; border-left: 4px solid #2563eb;">
            """
            for task in pending_tasks[:10]:  # Limit to 10 tasks
                priority_color = self._get_priority_color(task.get("priority", 3))
                pending_html += f"""
                    <div style="margin-bottom: 15px; padding: 10px; background-color: white; border-radius: 6px;">
                        <div style="display: flex; align-items: center; margin-bottom: 5px;">
                            <span style="background-color: {priority_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">
                                {self._get_priority_label(task.get("priority", 3))}
                            </span>
                            <strong style="color: #1f2937;">{task.get("title", "Untitled Task")}</strong>
                        </div>
                        <p style="color: #6b7280; margin: 5px 0; font-size: 14px;">{task.get("description", "No description") if task.get("description") else "No description"}</p>
                    </div>
                """

            if len(pending_tasks) > 10:
                pending_html += f"""
                    <p style="color: #6b7280; font-style: italic; margin-top: 10px;">
                        ... and {len(pending_tasks) - 10} more pending tasks
                    </p>
                """

            pending_html += """
                </div>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Daily Task Reminder</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); overflow: hidden;">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">📋 TodoList AI</h1>
                        <p style="color: rgba(255, 255, 255, 0.9); margin: 10px 0 0 0; font-size: 16px;">Your Daily Task Summary</p>
                    </div>

                    <!-- Content -->
                    <div style="padding: 30px;">
                        <p style="color: #374151; font-size: 16px; margin-bottom: 25px;">
                            Hi <strong>{username}</strong>,
                        </p>

                        <p style="color: #6b7280; font-size: 15px; line-height: 1.6; margin-bottom: 30px;">
                            Here's your daily summary of tasks that need your attention.
                        </p>

                        {expiring_html}
                        {pending_html}

                        <div style="margin-top: 40px; padding-top: 30px; border-top: 1px solid #e5e7eb; text-align: center;">
                            <a href="{settings.allowed_origins_list[0] if settings.allowed_origins_list else 'http://localhost:3000'}"
                               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 12px 30px; border-radius: 8px; font-weight: 500; font-size: 15px;">
                                View All Tasks
                            </a>
                        </div>
                    </div>

                    <!-- Footer -->
                    <div style="background-color: #f9fafb; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb;">
                        <p style="color: #9ca3af; font-size: 13px; margin: 0;">
                            You're receiving this email because you have email notifications enabled.
                        </p>
                        <p style="color: #9ca3af; font-size: 13px; margin: 10px 0 0 0;">
                            <a href="{settings.allowed_origins_list[0] if settings.allowed_origins_list else 'http://localhost:3000'}/settings"
                               style="color: #667eea; text-decoration: none;">
                                Manage your notification settings
                            </a>
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _generate_reminder_text(
        self,
        username: str,
        expiring_tasks: list[dict[str, Any]],
        pending_tasks: list[dict[str, Any]],
    ) -> str:
        """Generate plain text content for task reminder email."""
        text = f"Hi {username},\n\nHere's your daily summary of tasks that need your attention.\n\n"

        if expiring_tasks:
            text += "⏰ TASKS EXPIRING SOON:\n"
            text += "=" * 50 + "\n\n"
            for task in expiring_tasks:
                priority_label = self._get_priority_label(task.get("priority", 3))
                text += f"[{priority_label}] {task.get('title', 'Untitled Task')}\n"
                if task.get("description"):
                    text += f"   {task.get('description')}\n"
                text += f"   📅 Due: {task.get('due_date', 'Not set')}\n\n"

        if pending_tasks:
            text += "📝 PENDING TASKS:\n"
            text += "=" * 50 + "\n\n"
            for task in pending_tasks[:10]:
                priority_label = self._get_priority_label(task.get("priority", 3))
                text += f"[{priority_label}] {task.get('title', 'Untitled Task')}\n"
                if task.get("description"):
                    text += f"   {task.get('description')}\n\n"

            if len(pending_tasks) > 10:
                text += f"... and {len(pending_tasks) - 10} more pending tasks\n\n"

        text += "\n" + "=" * 50 + "\n"
        text += "View all your tasks at: " + (settings.allowed_origins_list[0] if settings.allowed_origins_list else "http://localhost:3000") + "\n\n"
        text += "To manage your notification settings, visit your account settings.\n"

        return text

    def _get_priority_color(self, priority: int) -> str:
        """Get color for priority level."""
        colors = {
            1: "#10b981",  # green - very low
            2: "#3b82f6",  # blue - low
            3: "#f59e0b",  # amber - medium
            4: "#f97316",  # orange - high
            5: "#ef4444",  # red - very high
        }
        return colors.get(priority, "#6b7280")

    def _get_priority_label(self, priority: int) -> str:
        """Get label for priority level."""
        labels = {
            1: "Very Low",
            2: "Low",
            3: "Medium",
            4: "High",
            5: "Very High",
        }
        return labels.get(priority, "Medium")


# Create singleton instance
email_service = EmailService()
