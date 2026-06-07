/**
 * Push Notifications Handler for Maes Mobilizadoras
 * Handles Firebase initialization, permission request, and token registration.
 */

(async () => {
  // 1. Fetch configuration from backend
  let config;
  try {
    const response = await fetch('/api/config');
    config = await response.json();
  } catch (e) {
    console.error('Failed to load frontend config:', e);
    return;
  }

  // If Firebase config is missing, we can't proceed
  if (!config.firebase || !config.firebase.apiKey) {
    console.warn('Firebase configuration missing in /api/config. Push notifications disabled.');
    return;
  }

  // 2. Load Firebase Scripts
  // We load them dynamically to keep it self-contained
  const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });

  try {
    // Using Firebase v10 compat for simplicity in this MPA environment
    await loadScript('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
    await loadScript('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');
  } catch (e) {
    console.error('Failed to load Firebase scripts:', e);
    return;
  }

  // 3. Initialize Firebase
  firebase.initializeApp(config.firebase);
  const messaging = firebase.messaging();

  /**
   * Registers the service worker and returns the registration
   */
  async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
        console.log('Service Worker registered with scope:', registration.scope);
        
        // Wait for service worker to be ready/active
        await navigator.serviceWorker.ready;
        
        return registration;
      } catch (err) {
        console.error('Service Worker registration failed:', err);
      }
    }
    return null;
  }

  /**
   * Registers the FCM token with the backend
   */
  async function registerToken(token) {

    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) return;

    try {
      const res = await fetch(`${config.api_base || ''}/api/me/fcm-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          token: token,
          device_type: 'web'
        })
      });

      if (res.ok) {
        console.log('FCM Token registered successfully');
      } else {
        console.error('Failed to register FCM Token:', await res.text());
      }
    } catch (e) {
      console.error('Error sending FCM token to backend:', e);
    }
  }

  /**
   * Requests permission and gets the token
   */
  async function requestPermissionAndGetToken() {
    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        console.log('Notification permission granted.');

        const swRegistration = await registerServiceWorker();
        if (!swRegistration) {
          console.error('Failed to register service worker.');
          return;
        }

        // Retry mechanism for getToken as Service Worker activation might take a moment
        let token = null;
        let retries = 5;
        while (retries > 0 && !token) {
          try {
            token = await messaging.getToken({
              vapidKey: config.firebase.vapidKey,
              serviceWorkerRegistration: swRegistration
            });
          } catch (e) {
            console.warn(`getToken attempt failed (${retries} retries left):`, e);
            retries--;
            if (retries > 0) await new Promise(r => setTimeout(r, 1000));
            else throw e;
          }
        }

        if (token) {
          await registerToken(token);
        } else {
          console.warn('No registration token available. Request permission to generate one.');
        }
      } else {
        console.warn('Unable to get permission to notify.');
      }
    } catch (err) {
      console.error('An error occurred while retrieving token. ', err);
    }
  }

  // 5. Handle foreground messages
  messaging.onMessage((payload) => {
    console.log('Message received in foreground: ', payload);
    // Show a custom notification or update UI
    const { title, body } = payload.notification;
    // Basic alert for now, can be improved with a custom toast
    if (confirm(`${title}\n\n${body}\n\n`)) {
      // Logic to navigate if needed
      if (payload.data && payload.data.url) {
        window.location.href = payload.data.url;
      }
    }
  });

  window.requestPermissionAndGetToken = requestPermissionAndGetToken;

})();
