// static/js/dashboard.js - Dashboard functionality

// Strategy action handlers
function viewStrategy(strategyId) {
    window.location.href = `/strategy/${strategyId}`;
}

function editStrategy(strategyId) {
    window.location.href = `/strategy/${strategyId}/edit`;
}

function deleteStrategy(strategyId) {
    if (confirm('Are you sure you want to delete this strategy? This action cannot be undone.')) {
        // Create a form and submit it
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/strategy/${strategyId}/delete`;
        
        // Add CSRF token if you're using one
        // const csrfToken = document.querySelector('meta[name="csrf-token"]');
        // if (csrfToken) {
        //     const tokenInput = document.createElement('input');
        //     tokenInput.type = 'hidden';
        //     tokenInput.name = '_token';
        //     tokenInput.value = csrfToken.getAttribute('content');
        //     form.appendChild(tokenInput);
        // }
        
        document.body.appendChild(form);
        form.submit();
    }
}

// Dark mode toggle
function toggleDarkMode() {
    const html = document.documentElement;
    const isDark = html.classList.contains('dark');
    
    if (isDark) {
        html.classList.remove('dark');
        localStorage.setItem('theme', 'light');
    } else {
        html.classList.add('dark');
        localStorage.setItem('theme', 'dark');
    }
}

// Initialize theme
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
    }
}

// Show success/error messages
function showMessage(message, type = 'info') {
    const messageContainer = document.getElementById('messageContainer');
    if (!messageContainer) return;
    
    const alertClasses = {
        'success': 'bg-green-50 border-green-200 text-green-800',
        'error': 'bg-red-50 border-red-200 text-red-800',
        'warning': 'bg-yellow-50 border-yellow-200 text-yellow-800',
        'info': 'bg-blue-50 border-blue-200 text-blue-800'
    };
    
    const iconClasses = {
        'success': 'text-green-400',
        'error': 'text-red-400',
        'warning': 'text-yellow-400',
        'info': 'text-blue-400'
    };
    
    const messageHTML = `
        <div class="border-l-4 p-4 ${alertClasses[type]} mb-4" id="alertMessage">
            <div class="flex">
                <div class="flex-shrink-0">
                    <svg class="h-5 w-5 ${iconClasses[type]}" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-auto pl-3">
                    <div class="-mx-1.5 -my-1.5">
                        <button onclick="dismissMessage()" class="inline-flex rounded-md p-1.5 hover:bg-gray-100 focus:outline-none">
                            <span class="sr-only">Dismiss</span>
                            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    messageContainer.innerHTML = messageHTML;
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        dismissMessage();
    }, 5000);
}

// Dismiss message
function dismissMessage() {
    const alertMessage = document.getElementById('alertMessage');
    if (alertMessage) {
        alertMessage.style.opacity = '0';
        alertMessage.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            alertMessage.remove();
        }, 300);
    }
}

// Check URL parameters for messages
function checkForMessages() {
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    const type = urlParams.get('type') || 'info';
    
    if (message) {
        showMessage(decodeURIComponent(message), type);
        
        // Clean URL without refreshing page
        const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
        window.history.pushState({path: newUrl}, '', newUrl);
    }
}

// Search functionality
function searchStrategies() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.toLowerCase();
    const strategyRows = document.querySelectorAll('[data-strategy-row]');
    
    strategyRows.forEach(row => {
        const strategyName = row.querySelector('[data-strategy-name]').textContent.toLowerCase();
        const strategyDesc = row.querySelector('[data-strategy-desc]')?.textContent.toLowerCase() || '';
        
        if (strategyName.includes(searchTerm) || strategyDesc.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
    
    // Show/hide empty state
    const visibleRows = document.querySelectorAll('[data-strategy-row]:not([style*="display: none"])');
    const emptyState = document.getElementById('emptySearchState');
    const strategiesTable = document.getElementById('strategiesTable');
    
    if (visibleRows.length === 0 && searchTerm.length > 0) {
        strategiesTable.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
    } else {
        strategiesTable.style.display = 'block';
        if (emptyState) emptyState.style.display = 'none';
    }
}

// Clear search
function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    searchInput.value = '';
    searchStrategies();
}

// Copy strategy code (for quick preview)
function copyStrategyCode(strategyId) {
    // This would make an AJAX call to get strategy code
    fetch(`/api/strategy/${strategyId}/code`)
        .then(response => response.json())
        .then(data => {
            navigator.clipboard.writeText(data.code).then(() => {
                showMessage('Strategy code copied to clipboard!', 'success');
            });
        })
        .catch(error => {
            showMessage('Failed to copy strategy code', 'error');
        });
}

// Bulk operations
function selectAllStrategies() {
    const checkboxes = document.querySelectorAll('[data-strategy-checkbox]');
    const selectAllCheckbox = document.getElementById('selectAllStrategies');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    updateBulkActions();
}

function updateBulkActions() {
    const checkedBoxes = document.querySelectorAll('[data-strategy-checkbox]:checked');
    const bulkActions = document.getElementById('bulkActions');
    
    if (checkedBoxes.length > 0) {
        bulkActions.style.display = 'block';
        document.getElementById('selectedCount').textContent = checkedBoxes.length;
    } else {
        bulkActions.style.display = 'none';
    }
}

function bulkDeleteStrategies() {
    const checkedBoxes = document.querySelectorAll('[data-strategy-checkbox]:checked');
    const strategyIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (strategyIds.length === 0) return;
    
    if (confirm(`Are you sure you want to delete ${strategyIds.length} strategies? This action cannot be undone.`)) {
        // Make API call to delete multiple strategies
        fetch('/api/strategies/bulk-delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ strategy_ids: strategyIds })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(`${strategyIds.length} strategies deleted successfully`, 'success');
                // Reload page or remove rows
                location.reload();
            } else {
                showMessage('Failed to delete strategies', 'error');
            }
        })
        .catch(error => {
            showMessage('Failed to delete strategies', 'error');
        });
    }
}

// Export strategies
function exportStrategies() {
    const checkedBoxes = document.querySelectorAll('[data-strategy-checkbox]:checked');
    const strategyIds = Array.from(checkedBoxes).map(cb => cb.value);
    
    if (strategyIds.length === 0) {
        showMessage('Please select strategies to export', 'warning');
        return;
    }
    
    // Create download link
    const downloadUrl = `/api/strategies/export?ids=${strategyIds.join(',')}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `strategies_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showMessage(`${strategyIds.length} strategies exported successfully`, 'success');
}

// Strategy statistics
function updateStatistics() {
    const totalStrategies = document.querySelectorAll('[data-strategy-row]').length;
    const totalStrategiesElement = document.getElementById('totalStrategies');
    
    if (totalStrategiesElement) {
        totalStrategiesElement.textContent = totalStrategies;
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    initializeTheme();
    
    // Check for URL messages
    checkForMessages();
    
    // Update statistics
    updateStatistics();
    
    // Add event listeners for strategy checkboxes
    const strategyCheckboxes = document.querySelectorAll('[data-strategy-checkbox]');
    strategyCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActions);
    });
    
    // Add search input listener
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', searchStrategies);
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('searchInput');
            if (searchInput && searchInput.value) {
                clearSearch();
            }
        }
    });
});