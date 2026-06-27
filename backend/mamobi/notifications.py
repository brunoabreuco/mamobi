import logging
import os
from typing import Dict, List, Optional
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import messaging
from mamobi.models import db, FCMToken

load_dotenv()
logger = logging.getLogger(__name__)
FIREBASE_CONF = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID"),
    "vapidKey": os.environ.get("FIREBASE_VAPID_KEY"),
}


def send_push_notification(
    token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
) -> bool:
    """
    Sends a push notification to a specific device token.
    Returns True if successful, False otherwise.
    If the token is invalid, it should be handled by the caller or this function.
    """
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        token=token,
    )

    try:
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True
    except messaging.UnregisteredError:
        logger.warning(f"Token unregistered: {token}. Deactivating in database.")
        _deactivate_token(token)
        return False
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False


def send_to_user(
    user_id: str, title: str, body: str, data: Optional[Dict[str, str]] = None
) -> int:
    """
    Sends a push notification to all active tokens of a user.
    Returns the number of successful sends.
    """
    active_tokens = FCMToken.query.filter_by(user_id=user_id, is_active=True).all()
    if not active_tokens:
        logger.info(f"No active FCM tokens found for user {user_id}")
        return 0

    success_count = 0
    for fcm_token in active_tokens:
        if send_push_notification(fcm_token.token, title, body, data):
            success_count += 1

    return success_count


def _deactivate_token(token: str):
    """
    Internal helper to mark a token as inactive.
    """
    try:
        fcm_token = FCMToken.query.filter_by(token=token).first()
        if fcm_token:
            fcm_token.is_active = False
            db.session.commit()
            logger.info(f"Token {token} marked as inactive.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to deactivate token {token}: {e}")
