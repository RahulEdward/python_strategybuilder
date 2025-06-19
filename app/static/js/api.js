// API client with authentication and error handling

const API_BASE_URL = '/api';

// Helper function to handle API responses
async function handleResponse(response) {
    const data = await response.json().catch(() => ({}));
    
    if (!response.ok) {
        const error = new Error(data.detail || 'An error occurred');
        error.status = response.status;
        error.data = data;
        throw error;
    }
    
    return data;
}

// Create headers with auth token
function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    };
    
    return headers;
}

// API client methods
export const api = {
    // Auth endpoints
    async getCurrentUser() {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            method: 'GET',
            headers: getAuthHeaders(),
            credentials: 'include' // This is crucial for sending cookies
        });
        return handleResponse(response);
    },
    
    async login(username, password) {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                username,
                password,
            }),
            credentials: 'include' // Include cookies in the request
        });
        return handleResponse(response);
    },
    
    async logout() {
        const response = await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        return handleResponse(response);
    },
    
    // Add other API methods here as needed
};

// Initialize auth state when the script loads
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Check auth status on page load
        const user = await api.getCurrentUser();
        document.dispatchEvent(new CustomEvent('auth:change', { detail: { user, isAuthenticated: true } }));
    } catch (error) {
        if (error.status !== 401) {
            console.error('Auth check failed:', error);
        }
        document.dispatchEvent(new CustomEvent('auth:change', { detail: { user: null, isAuthenticated: false } }));
    }
});
