import os
import threading
import time
import uuid
import socket
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask, send_from_directory
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from maes_mobilizadoras.app_factory import create_app
from maes_mobilizadoras.models import db, AuthOTP, User, FCMToken
from maes_mobilizadoras.notifications import send_to_user

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture(scope="module")
def server():
    # Setup a temporary database for the Selenium test
    db_path = os.path.abspath(f"test_{uuid.uuid4()}.db")
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SECRET_KEY": "test-secret-key-for-selenium",
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
    # Use the new headless mode which supports more features including alerts/confirm
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Avoid issues with self-signed certs or local origins if any
    options.add_argument("--allow-insecure-localhost")
    
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

@patch("maes_mobilizadoras.auth.TwilioClient")
def test_fcm_integration(mock_twilio_class, server, driver):
    # Mock Twilio instance
    mock_twilio_instance = mock_twilio_class.return_value
    mock_twilio_instance.messages.create.return_value = MagicMock()

    base_url, app = server
    
    # 1. Access the app
    driver.get(base_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "phone")))
    
    # 2. Login flow
    phone_input = driver.find_element(By.ID, "phone")
    # Use a unique phone number to avoid conflicts if anything is shared
    unique_suffix = str(uuid.uuid4().int)[:6]
    phone_number = f"11999{unique_suffix}"
    phone_input.send_keys(phone_number)
    
    submit_button = driver.find_element(By.CSS_SELECTOR, ".etapa01-telefone button")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(submit_button))
    submit_button.click()
    
    # Wait for OTP to be generated in DB
    # We poll instead of sleep
    db_phone = "+55" + phone_number
    otp = None
    for _ in range(10):
        with app.app_context():
            otp = AuthOTP.query.filter_by(phone=db_phone).order_by(AuthOTP.created_at.desc()).first()
            if otp:
                break
        time.sleep(1)
    
    assert otp is not None, f"OTP not found for {db_phone}"
    code = otp.code
    
    # Enter OTP
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "input-codigo")))
    otp_inputs = driver.find_elements(By.CLASS_NAME, "input-codigo")
    for i, digit in enumerate(code):
        otp_inputs[i].send_keys(digit)
    
    # Wait for name/bairro step (Etapa 3) to be visible
    name_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "name")))
    name_input.send_keys("Selenium User")
    
    # Click finalize
    finalize_button = driver.find_element(By.CSS_SELECTOR, ".etapa04-nome-bairro a")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(finalize_button))
    finalize_button.click()
    
    # Wait for final redirect
    WebDriverWait(driver, 20).until(EC.url_contains("tela_acoes_comunitarias.html"))
    
    # 3. Trigger FCM permission and registration
    # In a real scenario, this might be triggered by a user action or on load.
    # We call it explicitly to ensure it runs.
    driver.execute_script("if(window.requestPermissionAndGetToken) window.requestPermissionAndGetToken();")
    
    # Wait for token to be registered in DB
    # This interacts with real Firebase, so it might take a few seconds
    max_retries = 30
    token_found = False
    user_id = None
    with app.app_context():
        user = User.query.filter_by(phone=db_phone).first()
        user_id = user.id
        
    for i in range(max_retries):
        with app.app_context():
            token = FCMToken.query.filter_by(user_id=user_id, is_active=True).first()
            if token:
                token_found = True
                break
        time.sleep(1)
    
    assert token_found, "FCM Token was not registered in the database. Make sure Firebase config is valid and browser can reach it."
    
    # 4. Trigger a push notification from the backend
    with app.app_context():
        success_count = send_to_user(user_id, "Teste Selenium", "Olá do teste!")
        assert success_count > 0, "Failed to send push notification via Firebase. Check server logs."
    
    # 5. Verify notification on frontend
    # notifications.js:
    # messaging.onMessage((payload) => {
    #   if (confirm(`${title}\n\n${body}\n\n`)) { ... }
    # });
    
    WebDriverWait(driver, 30).until(EC.alert_is_present())
    alert = driver.switch_to.alert
    assert "Teste Selenium" in alert.text
    assert "Olá do teste!" in alert.text
    alert.accept()
