document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Chat functionality
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');
    const chatbox = document.getElementById('chatbox');

    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const queryInput = document.getElementById('queryInput');
            const query = queryInput.value;

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
                    let eventsHtml = '<div class="mt-2"><strong>Found Events:</strong><ul class="list-unstyled">';
                    data.events.forEach(event => {
                        eventsHtml += `
                            <li class="mt-2">
                                <div class="card">
                                    <div class="card-body">
                                        <h6 class="card-title">${event.title}</h6>
                                        <p class="card-text small">
                                            <strong>Date:</strong> ${event.date}<br>
                                            <strong>Location:</strong> ${event.location}<br>
                                            <strong>Risk Level:</strong> ${event.risk_level}
                                        </p>
                                        <a href="/report/${event.id}" class="btn btn-sm btn-secondary">View Details</a>
                                    </div>
                                </div>
                            </li>`;
                    });
                    eventsHtml += '</ul></div>';
                    addMessageToChat('assistant', eventsHtml, true);
                }
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
    messageDiv.className = `chat-message mb-2 ${role === 'user' ? 'text-end' : ''}`;

    const messageContent = document.createElement('div');
    messageContent.className = `d-inline-block p-2 rounded ${role === 'user' ? 'bg-primary' : 'bg-secondary'}`;

    if (isHTML) {
        messageContent.innerHTML = content;
    } else {
        messageContent.textContent = content;
    }

    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Function to toggle chat visibility
function toggleChat() {
    const chatbox = document.getElementById('chatbox');
    chatbox.style.display = chatbox.style.display === 'none' ? 'block' : 'none';
}