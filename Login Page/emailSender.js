document.addEventListener('DOMContentLoaded', () => {
    const emailForm = document.getElementById('emailForm');
    const emailInput = document.getElementById('emailInput');
    const emailStatus = document.getElementById('emailStatus');

    emailForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = emailInput.value;
        const code = document.getElementById('codeDisplay').textContent;

        emailStatus.textContent = 'Sending email...';

        try {
            // Simulate sending an email (always succeeds)
            await simulateSendEmail(email, code);
            emailStatus.textContent = `Joining code sent to ${email}`;
            emailInput.value = ''; // Clear the input field
        } catch (error) {
            // This catch block will never be reached in this simulation
            emailStatus.textContent = 'Failed to send email. Please try again.';
            console.error('Error sending email:', error);
        }
    });
});

// This function simulates sending an email
// In a real application, this would be replaced with an actual API call
function simulateSendEmail(email, code) {
    return new Promise((resolve) => {
        setTimeout(() => {
            console.log(`Email sent to ${email} with code: ${code}`);
            resolve();
        }, 2000); // Simulate a 2-second delay
    });
}