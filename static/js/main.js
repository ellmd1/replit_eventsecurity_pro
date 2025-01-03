document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

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
                addMessageToChat('assistant', data.response, false, true, query);

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

    // Add event delegation for save to log buttons
    chatMessages.addEventListener('click', async function(e) {
        if (e.target.classList.contains('save-to-log') || e.target.closest('.save-to-log')) {
            const button = e.target.classList.contains('save-to-log') ? e.target : e.target.closest('.save-to-log');
            const messageContent = button.closest('.message-content');
            const responseText = messageContent.getAttribute('data-response');
            const questionText = messageContent.getAttribute('data-question');

            try {
                const response = await fetch('/decisions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        description: `Question: ${questionText}\n\nAI Assistant Response: ${responseText}`,
                        author: 'AI Assistant'
                    })
                });

                const result = await response.json();
                if (result.status === 'success') {
                    button.innerHTML = '<i data-feather="check"></i>';
                    button.classList.remove('btn-outline-light');
                    button.classList.add('btn-success');
                    feather.replace();
                    setTimeout(() => {
                        button.innerHTML = '<i data-feather="save"></i>';
                        button.classList.remove('btn-success');
                        button.classList.add('btn-outline-light');
                        feather.replace();
                    }, 2000);
                }
            } catch (error) {
                console.error('Error saving to decision log:', error);
                button.innerHTML = '<i data-feather="alert-circle"></i>';
                button.classList.remove('btn-outline-light');
                button.classList.add('btn-danger');
                feather.replace();
                setTimeout(() => {
                    button.innerHTML = '<i data-feather="save"></i>';
                    button.classList.remove('btn-danger');
                    button.classList.add('btn-outline-light');
                    feather.replace();
                }, 2000);
            }
        }
    });
});

// Helper function to add messages to chat
function addMessageToChat(role, content, isHTML = false, addSaveButton = false, question = '') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;

    const messageContent = document.createElement('div');
    messageContent.className = `message-content rounded p-3`;

    if (isHTML) {
        messageContent.innerHTML = content;
    } else {
        if (addSaveButton) {
            messageContent.setAttribute('data-response', content);
            messageContent.setAttribute('data-question', question);
            const saveButton = document.createElement('button');
            saveButton.className = 'btn btn-sm btn-outline-light save-to-log';
            saveButton.innerHTML = '<i data-feather="save"></i>';
            saveButton.title = 'Save to Decision Log';
            messageContent.appendChild(saveButton);
        }
        messageContent.appendChild(document.createTextNode(content));
    }

    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Initialize Feather icons for new content
    if (addSaveButton) {
        feather.replace();
    }
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