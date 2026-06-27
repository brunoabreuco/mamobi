import pytest
from unittest.mock import patch, MagicMock
from mamobi.models import User, FCMToken, db
from mamobi.notifications import send_push_notification, send_to_user
from mamobi.auth import issue_tokens

def _create_user(app, **kwargs) -> str:
    defaults = {
        "phone": "+5511999990000",
        "full_name": "Maria Teste",
        "neighborhood": "Centro",
        "role": "participante",
        "is_active": True,
    }
    defaults.update(kwargs)
    with app.app_context():
        user = User(**defaults)
        db.session.add(user)
        db.session.commit()
        return user.id

def _auth_header(app, user_id: str) -> dict:
    with app.app_context():
        user = db.session.get(User, user_id)
        tokens = issue_tokens(str(user.id), user.role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}

@pytest.fixture
def mock_messaging():
    from firebase_admin import messaging
    with patch('mamobi.notifications.messaging') as mock:
        # Ensure the mock's UnregisteredError refers to the real class
        # so that 'except messaging.UnregisteredError' works in the app code
        mock.UnregisteredError = messaging.UnregisteredError
        yield mock

def test_send_push_notification_success(app, mock_messaging):
    mock_messaging.send.return_value = "projects/test/messages/123"
    
    with app.app_context():
        success = send_push_notification("fake-token", "Title", "Body")
        assert success is True
        mock_messaging.send.assert_called_once()

def test_send_push_notification_unregistered(app, mock_messaging):
    from firebase_admin import messaging
    mock_messaging.send.side_effect = messaging.UnregisteredError("Token unregistered")
    
    with app.app_context():
        # Create a user and token to test deactivation
        user_id = _create_user(app, phone="5511999999999")
        
        token = FCMToken(user_id=user_id, token="bad-token", is_active=True)
        db.session.add(token)
        db.session.commit()
        
        success = send_push_notification("bad-token", "Title", "Body")
        assert success is False
        
        # Verify it was deactivated
        token_after = db.session.get(FCMToken, (user_id, "bad-token"))
        assert token_after.is_active is False

def test_send_to_user(app, mock_messaging):
    mock_messaging.send.return_value = "ok"
    
    with app.app_context():
        user_id = _create_user(app, phone="5511988888888")
        
        token1 = FCMToken(user_id=user_id, token="token1", is_active=True)
        token2 = FCMToken(user_id=user_id, token="token2", is_active=True)
        token3 = FCMToken(user_id=user_id, token="token3", is_active=False) # Inactive
        db.session.add_all([token1, token2, token3])
        db.session.commit()
        
        count = send_to_user(user_id, "Hello", "World")
        assert count == 2
        assert mock_messaging.send.call_count == 2

def test_register_fcm_token_new(client, app):
    # Test registering a brand new token
    uid = _create_user(app, phone="5511977770001")
    headers = _auth_header(app, uid)
    
    response = client.post(
        "/api/me/fcm-token",
        json={"token": "new-token-123", "device_type": "android"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json["message"] == "token_registered"
    
    with app.app_context():
        token = FCMToken.query.filter_by(token="new-token-123").first()
        assert token is not None
        assert token.user_id == uid

def test_register_fcm_token_update_existing(client, app):
    # Test updating an existing token (upsert)
    uid1 = _create_user(app, phone="5511977770002")
    uid2 = _create_user(app, phone="5511977770003")
    
    with app.app_context():
        token = FCMToken(user_id=uid1, token="shared-token", device_type="web", is_active=True)
        db.session.add(token)
        db.session.commit()

    headers = _auth_header(app, uid2)
    # Now register via API with the same token but for uid2
    response = client.post(
        "/api/me/fcm-token",
        json={"token": "shared-token", "device_type": "ios"},
        headers=headers
    )
    assert response.status_code == 200
    
    with app.app_context():
        updated_token = FCMToken.query.filter_by(token="shared-token").first()
        assert updated_token.user_id == uid2
        assert updated_token.device_type == "ios"

def test_send_push_notification_general_exception(app, mock_messaging):
    # Test that we handle unexpected Firebase errors gracefully
    mock_messaging.send.side_effect = Exception("Firebase is down")
    
    with app.app_context():
        success = send_push_notification("any-token", "Title", "Body")
        assert success is False

def test_send_to_user_no_tokens(app, mock_messaging):
    # Test sending to a user with no registered tokens
    with app.app_context():
        user_id = _create_user(app, phone="5511966666666")
        
        count = send_to_user(user_id, "Hi", "There")
        assert count == 0
        assert mock_messaging.send.call_count == 0
