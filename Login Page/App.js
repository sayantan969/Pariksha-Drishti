import { signInWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/10.13.1/firebase-auth.js";

document.addEventListener('DOMContentLoaded', () => {
    const authForm = document.getElementById('auth-form');
    const errorMessage = document.getElementById('error-message');
    const loadingElement = document.getElementById('loading');

    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        errorMessage.textContent = '';
        loadingElement.style.display = 'block';

        try {
            // Sign in with Firebase
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            
            // Get the ID token
            const idToken = await userCredential.user.getIdToken(true);

            // Send the ID token to your Flask backend
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'id_token=' + encodeURIComponent(idToken)
            });

            const data = await response.json();

            if (response.ok) {
                // Successful login
                alert('Login Successful! Redirecting to dashboard...');
                window.location.href = "/"; // Redirect to the main page or dashboard
            } else {
                // Server-side authentication failed
                throw new Error(data.error || 'Server authentication failed');
            }
        } catch (error) {
            errorMessage.textContent = error.message;
        } finally {
            loadingElement.style.display = 'none';
        }
    });
});