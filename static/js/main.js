document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Add right-click context menu
    document.addEventListener('contextmenu', function(e) {
        const selectedText = window.getSelection().toString().trim();
        if (selectedText) {
            e.preventDefault();
            
            const contextMenu = document.createElement('div');
            contextMenu.className = 'context-menu';
            contextMenu.innerHTML = `
                <div class="context-menu-item" data-action="copy-to-log">
                    <i data-feather="clipboard"></i> Copy to Decision Log
                </div>
            `;
            
            contextMenu.style.left = e.pageX + 'px';
            contextMenu.style.top = e.pageY + 'px';
            document.body.appendChild(contextMenu);
            feather.replace();

            // Handle menu item click
            contextMenu.querySelector('[data-action="copy-to-log"]').addEventListener('click', function() {
                addToDecisionLog(selectedText);
                contextMenu.remove();
            });

            // Remove menu when clicking elsewhere
            document.addEventListener('click', function cleanup() {
                contextMenu.remove();
                document.removeEventListener('click', cleanup);
            });
        }
    });

    // Chat functionality
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');
    const queryInput = document.getElementById('queryInput');

    // Example prompts functionality
    document.querySelectorAll('.example-prompt').forEach(button => {
        button.addEventListener('click', function() {
            if (queryInput) {
                queryInput.value = this.textContent.trim();
                queryInput.focus();
            }
        });
    });

    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const query = queryInput.value.trim();
            if (!query) return;

            // Add user message to chat
            addMessageToChat('user', query);
            queryInput.value = '';

            try {
                const response = await fetch('/chat_query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query })
                });

                const data = await response.json();

                // Add response to chat
                addMessageToChat('assistant', data.response);

                // If there are events in the response, display them
                if (data.events && data.events.length > 0) {
                    let eventsHtml = `<div class="mt-2">
                        <div class="text-muted small mb-2">Found ${data.events.length} relevant events:</div>
                        <div class="d-flex flex-column gap-2">`;

                    data.events.forEach(event => {
                        eventsHtml += `
                            <div class="event-card p-3 rounded">
                                <div class="d-flex justify-content-between align-items-start">
                                    <h6 class="mb-1">${event.title}</h6>
                                    <span class="badge bg-${getRiskLevelClass(event.risk_level)}">
                                        ${event.risk_level} Risk
                                    </span>
                                </div>
                                <div class="small text-muted mb-2">
                                    <i data-feather="calendar" class="feather-sm me-1"></i> ${event.date}
                                    <br>
                                    <i data-feather="map-pin" class="feather-sm me-1"></i> ${event.location}
                                    <br>
                                    <i data-feather="users" class="feather-sm me-1"></i> ${event.attendance || 'Not recorded'} attendees
                                </div>
                                ${event.security_measures ? `
                                    <div class="small mb-2">
                                        <strong>Security Measures:</strong><br>
                                        ${event.security_measures}
                                    </div>
                                ` : ''}
                                ${event.incidents_reported ? `
                                    <div class="small mb-2">
                                        <strong>Incidents:</strong> ${event.incidents_reported}
                                        ${event.incident_summary ? `<br>${event.incident_summary}` : ''}
                                    </div>
                                ` : ''}
                                <div class="mt-2">
                                    <a href="/report/${event.id}" class="btn btn-sm btn-secondary">
                                        View Full Details
                                    </a>
                                </div>
                            </div>`;
                    });
                    eventsHtml += '</div></div>';
                    addMessageToChat('assistant', eventsHtml, true);
                }

                // Initialize Feather icons for new content
                feather.replace();

                // Focus input for next message
                queryInput.focus();

            } catch (error) {
                console.error('Error:', error);
                addMessageToChat('assistant', 'Sorry, I encountered an error processing your query.');
            }
        });
    }
});

// Helper function to add messages to chat
function addMessageToChat(role, content, isHTML = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const messageContent = document.createElement('div');
    messageContent.className = `message-content rounded p-3`;

    if (isHTML) {
        messageContent.innerHTML = content;
    } else {
        messageContent.textContent = content;
    }

    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Helper function to get Bootstrap color class based on risk level
function getRiskLevelClass(riskLevel) {
    switch (riskLevel) {
        case 'High':
            return 'danger';
        case 'Medium':
            return 'warning';
        case 'Low':
            return 'success';
        default:
            return 'secondary';
    }
}
// Add text to decision log
function addToDecisionLog(text) {
    fetch('/add_decision', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            decision_type: 'text_selection',
            details: text
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('Added to decision log');
        }
    });
}

// Show notification
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 2000);
}
