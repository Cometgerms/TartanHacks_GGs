// Backend API URL
const BACKEND_URL = 'http://localhost:5000';

// Check server status on load
document.addEventListener('DOMContentLoaded', () => {
    checkServerStatus();
    setupEventListeners();
});

// Check both frontend and backend status
async function checkServerStatus() {
    // Check frontend
    try {
        const frontendResponse = await fetch('/api/frontend-health');
        const frontendData = await frontendResponse.json();
        updateStatus('frontend-status', true, frontendData.message);
    } catch (error) {
        updateStatus('frontend-status', false, 'Frontend server error');
    }

    // Check backend
    try {
        const backendResponse = await fetch(`${BACKEND_URL}/api/health`);
        const backendData = await backendResponse.json();
        updateStatus('backend-status', true, backendData.message);
    } catch (error) {
        updateStatus('backend-status', false, 'Cannot connect to backend');
        console.error('Backend connection error:', error);
    }
}

// Update status display
function updateStatus(elementId, isOnline, message) {
    const statusElement = document.getElementById(elementId);
    statusElement.textContent = message;
    statusElement.className = `status ${isOnline ? 'online' : 'offline'}`;
}

// Setup event listeners
function setupEventListeners() {
    const fetchDataBtn = document.getElementById('fetch-data-btn');
    const dataForm = document.getElementById('data-form');

    fetchDataBtn.addEventListener('click', fetchDataFromBackend);
    dataForm.addEventListener('submit', sendDataToBackend);
}

// Fetch data from backend
async function fetchDataFromBackend() {
    const dataContainer = document.getElementById('data-container');
    dataContainer.innerHTML = '<p>Loading...</p>';

    try {
        const response = await fetch(`${BACKEND_URL}/api/data`);
        const result = await response.json();

        if (result.data && result.data.length > 0) {
            dataContainer.innerHTML = result.data.map(item => `
                <div class="data-item">
                    <h3>${item.name}</h3>
                    <p><strong>ID:</strong> ${item.id}</p>
                    <p><strong>Description:</strong> ${item.description}</p>
                </div>
            `).join('');
        } else {
            dataContainer.innerHTML = '<p>No data available</p>';
        }
    } catch (error) {
        dataContainer.innerHTML = `
            <div class="error-message">
                <strong>Error:</strong> Could not fetch data from backend. 
                Make sure the backend server is running on ${BACKEND_URL}
            </div>
        `;
        console.error('Fetch error:', error);
    }
}

// Send data to backend
async function sendDataToBackend(event) {
    event.preventDefault();
    
    const nameInput = document.getElementById('name-input');
    const messageInput = document.getElementById('message-input');
    const responseContainer = document.getElementById('response-container');

    const data = {
        name: nameInput.value,
        message: messageInput.value,
        timestamp: new Date().toISOString()
    };

    responseContainer.innerHTML = '<p>Sending...</p>';

    try {
        const response = await fetch(`${BACKEND_URL}/api/data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        responseContainer.innerHTML = `
            <div class="success-message">
                <strong>Success!</strong> ${result.message}
                <pre>${JSON.stringify(result.received_data, null, 2)}</pre>
            </div>
        `;

        // Clear form
        nameInput.value = '';
        messageInput.value = '';
    } catch (error) {
        responseContainer.innerHTML = `
            <div class="error-message">
                <strong>Error:</strong> Could not send data to backend. 
                Make sure the backend server is running on ${BACKEND_URL}
            </div>
        `;
        console.error('Send error:', error);
    }
}
