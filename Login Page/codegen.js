function generateAlphanumericCode(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
}

function updateCode() {
    const codeDisplay = document.getElementById('codeDisplay');
    codeDisplay.textContent = generateAlphanumericCode(10);
}

document.addEventListener('DOMContentLoaded', () => {
    const regenerateBtn = document.getElementById('regenerateBtn');
    regenerateBtn.addEventListener('click', updateCode);
    
    // Generate initial code
    updateCode();
});