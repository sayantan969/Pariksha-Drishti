// Firebase configuration (replace with your own)
const firebaseConfig = {
    apiKey: "AIzaSyBaLSzmG-JAUz00AHIj5yVMZEuaQQ8_CuI",
    authDomain: "ai-proctor-11d4a.firebaseapp.com",
    projectId: "ai-proctor-11d4a",
    storageBucket: "ai-proctor-11d4a.appspot.com",
    messagingSenderId: "544088826517",
    appId: "1:544088826517:web:c681d23b7e4c70cc37b19c",
    measurementId: "G-194Q0T5M8F"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Reference to the authentication service
const auth = firebase.auth();

// Handle login form submission
document.getElementById('login-form').addEventListener('submit', (e) => {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorMessage = document.getElementById('error-message');

    errorMessage.textContent = ''; // Clear any previous error

    // Log in existing user
    auth.signInWithEmailAndPassword(email, password)
        .then((userCredential) => {
            // Get the user's ID token
            return userCredential.user.getIdToken(true);
        })
        .then((idToken) => {
            // Send the ID token to your server
            return fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'id_token=' + encodeURIComponent(idToken)
            });
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Server authentication failed');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            // Show success message and redirect
            alert('Login Successful! Redirecting to dashboard...');
            window.location.href = "/"; // Redirect to the main page or dashboard
        })
        .catch((error) => {
            errorMessage.textContent = error.message;
        });
});