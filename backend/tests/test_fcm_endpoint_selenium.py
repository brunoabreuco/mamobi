import os
import threading
import time
import uuid
import socket
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import pytest
import requests
from flask import Flask, send_from_directory
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from maes_mobilizadoras.app_factory import create_app
from maes_mobilizadoras.models import db, AuthOTP, User, FCMToken, Event, EventCategory, EventParticipation
from maes_mobilizadoras.auth import issue_tokens

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture(scope="module")
def server():
    # Setup a temporary database for the Selenium test
    db_path = os.path.abspath(f"test_notify_{uuid.uuid4()}.db")
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-secret-key-for-selenium-notify",
        "RATELIMIT_ENABLED": False,
    }
    
    app = create_app(test_config=test_config)
    
    # Add a root route for testing if not present
    if '/' not in [str(p) for p in app.url_map.iter_rules()]:
        @app.route('/')
        def index():
            return send_from_directory(app.static_folder, 'tela-cadastro.html')
    
    with app.app_context():
        db.create_all()
        # Seed a category
        cat = EventCategory(name="Geral", icon="info", color="#000000")
        db.session.add(cat)
        db.session.commit()
    
    port = get_free_port()
    server_thread = threading.Thread(target=app.run, kwargs={"port": port, "debug": False, "use_reloader": False})
    server_thread.daemon = True
    server_thread.start()
    
    # Give it a moment to start
    time.sleep(2)
    
    yield f"http://localhost:{port}", app
    
    # Cleanup
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass

@pytest.fixture(scope="module")
def driver():
    options = Options()
    # Enable notifications
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 1
    })
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--allow-insecure-localhost")
    
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

@patch("maes_mobilizadoras.auth.TwilioClient")
def test_fcm_notify_endpoint(mock_twilio_class, server, driver):
    # Mock Twilio instance
    mock_twilio_instance = mock_twilio_class.return_value
    mock_twilio_instance.messages.create.return_value = MagicMock()

    base_url, app = server
    
    # 1. Setup Organizer and Participant in DB
    with app.app_context():
        # Organizer
        org = User(
            id=str(uuid.uuid4()),
            phone="+5511888888888",
            full_name="Organizadora",
            neighborhood="Bairro",
            role="organizadora",
            is_active=True
        )
        db.session.add(org)
        
        # Participant
        part_phone_number = f"11998{str(uuid.uuid4().int)[:6]}"
        db_part_phone = "+55" + part_phone_number
        part = User(
            id=str(uuid.uuid4()),
            phone=db_part_phone,
            full_name="Participante",
            neighborhood="Bairro",
            role="participante",
            is_active=True
        )
        db.session.add(part)
        
        # Event
        cat = EventCategory.query.first()
        event = Event(
            id=str(uuid.uuid4()),
            title="Evento de Teste",
            description="Desc",
            event_datetime=datetime.now(timezone.utc) + timedelta(days=1),
            location_name="Local",
            category_id=cat.id,
            organizer_id=org.id,
            status="active"
        )
        db.session.add(event)
        
        # Participation
        participation = EventParticipation(
            event_id=event.id,
            user_id=part.id,
            status="confirmed"
        )
        db.session.add(participation)
        db.session.commit()
        
        org_id = org.id
        event_id = event.id
        part_id = part.id
        
        # Issue token for the organizer to call the endpoint later
        org_tokens = issue_tokens(org_id, "organizadora")
        org_access_token = org_tokens["access_token"]

    # 2. Login Participant via Selenium to register FCM
    driver.get(base_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "phone")))
    
    phone_input = driver.find_element(By.ID, "phone")
    phone_input.send_keys(part_phone_number)
    
    submit_button = driver.find_element(By.CSS_SELECTOR, ".etapa01-telefone button")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(submit_button))
    submit_button.click()
    
    # Wait and get OTP
    otp = None
    for _ in range(10):
        with app.app_context():
            otp = AuthOTP.query.filter_by(phone=db_part_phone).order_by(AuthOTP.created_at.desc()).first()
            if otp:
                break
        time.sleep(1)
    
    assert otp is not None
    
    otp_inputs = driver.find_elements(By.CLASS_NAME, "input-codigo")
    for i, digit in enumerate(otp.code):
        otp_inputs[i].send_keys(digit)
    
    # Should redirect directly if name already present (it is in our case)
    # Wait for final redirect
    WebDriverWait(driver, 20).until(EC.url_contains("tela_acoes_comunitarias.html"))
    
    # Trigger FCM registration
    # Wait a bit for the script to load and initialize
    time.sleep(2)
    driver.execute_script("if(window.requestPermissionAndGetToken) window.requestPermissionAndGetToken();")
    
    # Wait for token registration
    token_registered = False
    for _ in range(30):
        with app.app_context():
            token = FCMToken.query.filter_by(user_id=part_id, is_active=True).first()
            if token:
                token_registered = True
                break
        time.sleep(1)
    
    assert token_registered, "FCM Token not registered for participant"

    # 3. Call the notify endpoint acting as the Organizer
    notify_url = f"{base_url}/api/acoes/{event_id}/notify"
    notify_payload = {
        "title": "Aviso Urgente",
        "message": "O evento mudou de lugar!"
    }
    headers = {
        "Authorization": f"Bearer {org_access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(notify_url, json=notify_payload, headers=headers)
    assert response.status_code == 201
    
    # 4. Verify notification in Participant's browser
    WebDriverWait(driver, 30).until(EC.alert_is_present())
    alert = driver.switch_to.alert
    assert "Aviso Urgente" in alert.text
    assert "O evento mudou de lugar!" in alert.text
    alert.accept()
