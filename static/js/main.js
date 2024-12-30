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
            queryInput.value = this.textContent.trim();
            queryInput.focus();
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

    // Handle access log form submission
    const accessLogForm = document.getElementById('accessLogForm');
    if (accessLogForm) {
        accessLogForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const reportId = this.dataset.reportId;
            const assessorName = this.elements.assessorName.value;
            const purpose = this.elements.purpose.value;
            const assessmentContext = this.elements.assessmentContext.value;
            const similarEventDetails = this.elements.similarEventDetails.value;

            try {
                const response = await fetch('/log_access', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        report_id: reportId,
                        assessor_name: assessorName,
                        purpose: purpose,
                        assessment_context: assessmentContext,
                        similar_event_details: similarEventDetails
                    })
                });

                const data = await response.json();
                if (data.status === 'success') {
                    alert('Access logged successfully');
                    this.reset();
                } else {
                    alert('Error logging access: ' + data.message);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error logging access');
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