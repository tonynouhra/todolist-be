"""
Push Subscription model for storing web push notification subscriptions.

This module defines the PushSubscription model which manages user subscriptions
to web push notifications for browser-based notifications.
"""

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from .base import UUID, BaseModel


class PushSubscription(BaseModel):
    """
    Represents a push notification subscription for a user.

    This class stores the subscription information needed to send
    web push notifications to a user's browser.

    :ivar user_id: Foreign key reference to the user.
    :type user_id: UUID
    :ivar endpoint: Push service endpoint URL.
    :type endpoint: str
    :ivar p256dh_key: User's public key for encryption (p256dh).
    :type p256dh_key: str
    :ivar auth_key: Authentication secret for the subscription.
    :type auth_key: str
    :ivar user_agent: Browser user agent string (optional).
    :type user_agent: str
    """

    __tablename__ = "push_subscriptions"

    # Foreign key to user
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Push subscription details
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh_key = Column(String(255), nullable=False)  # Public key for encryption
    auth_key = Column(String(255), nullable=False)  # Authentication secret

    # Optional metadata
    user_agent = Column(String(500))  # Browser/device info

    # Relationship
    user = relationship("User", back_populates="push_subscriptions")
