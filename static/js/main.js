document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Chat functionality
    const chatForm = document.getElementById('chatForm');
    const persistentChatForm = document.getElementById('persistentChatForm');
    const chatMessages = document.getElementById('chatMessages');
    const chatHistory = document.getElementById('chatHistory');
    const queryInput = document.getElementById('queryInput');
    const persistentChatInput = document.getElementById('persistentChatInput');
    const chatSidebar = document.getElementById('chatSidebar');
    const chatToggle = document.getElementById('chatToggle');
    const mainContent = document.querySelector('.main-content');

    // Load chat history from session storage
    const loadChatHistory = () => {
        const history = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');
        if (chatHistory) {
            chatHistory.innerHTML = ''; // Clear existing messages
            history.forEach(msg => {
                addMessageToHistory(msg.role, msg.content, msg.isHTML, msg.addSaveButton, msg.question, msg.timestamp);
            });
        }
    };

    // Save chat history to session storage
    const saveChatHistory = () => {
        const messages = Array.from(chatHistory.children).map(msg => ({
            role: msg.classList.contains('user') ? 'user' : 'assistant',
            content: msg.querySelector('.message-content').getAttribute('data-content'),
            isHTML: msg.querySelector('.message-content').getAttribute('data-is-html') === 'true',
            addSaveButton: msg.querySelector('.message-content').getAttribute('data-save-button') === 'true',
            question: msg.querySelector('.message-content').getAttribute('data-question') || '',
            timestamp: msg.querySelector('.chat-timestamp')?.textContent || new Date().toLocaleString()
        }));
        sessionStorage.setItem('chatHistory', JSON.stringify(messages));
    };

    // Add message to chat history
    function addMessageToHistory(role, content, isHTML = false, addSaveButton = false, question = '', timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        if (!sessionStorage.getItem(`read_${timestamp}`)) {
            messageDiv.classList.add('unread');
        }

        const messageContent = document.createElement('div');
        messageContent.className = `message-content rounded p-2`;
        messageContent.setAttribute('data-content', content);
        messageContent.setAttribute('data-is-html', isHTML);
        messageContent.setAttribute('data-save-button', addSaveButton);
        messageContent.setAttribute('data-question', question);

        if (isHTML) {
            messageContent.innerHTML = content;
        } else {
            if (addSaveButton) {
                const saveButton = document.createElement('button');
                saveButton.className = 'btn btn-sm btn-outline-light save-to-log';
                saveButton.innerHTML = '<i data-feather="save"></i>';
                saveButton.title = 'Save to Decision Log';
                messageContent.appendChild(saveButton);
            }
            messageContent.appendChild(document.createTextNode(content));
        }

        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'chat-timestamp';
        timestampDiv.textContent = timestamp || new Date().toLocaleString();
        messageContent.appendChild(timestampDiv);

        messageDiv.appendChild(messageContent);
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        if (addSaveButton) {
            feather.replace();
        }

        // Mark message as read when clicked
        messageDiv.addEventListener('click', function() {
            if (this.classList.contains('unread')) {
                this.classList.remove('unread');
                sessionStorage.setItem(`read_${timestamp}`, 'true');
            }
        });

        // Save to session storage
        saveChatHistory();
    }

    // Toggle chat sidebar
    if (chatToggle) {
        chatToggle.addEventListener('click', () => {
            chatSidebar.classList.toggle('collapsed');
            chatToggle.classList.toggle('collapsed');
            mainContent.style.marginLeft = chatSidebar.classList.contains('collapsed') ? '0' : 'var(--chat-sidebar-width)';
        });
    }

    // Handle persistent chat form submission
    if (persistentChatForm) {
        persistentChatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const query = persistentChatInput.value.trim();
            if (!query) return;

            // Add user message to chat
            addMessageToHistory('user', query);
            persistentChatInput.value = '';

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
                addMessageToHistory('assistant', data.response, false, true, query);

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
                    addMessageToHistory('assistant', eventsHtml, true);
                }

                // Initialize Feather icons for new content
                feather.replace();

                // Save updated chat history
                saveChatHistory();

            } catch (error) {
                console.error('Error:', error);
                addMessageToHistory('assistant', 'Sorry, I encountered an error processing your query.');
            }
        });
    }

    // Example prompts functionality
    document.querySelectorAll('.example-prompt').forEach(button => {
        button.addEventListener('click', function() {
            const input = document.getElementById('queryInput') || document.getElementById('persistentChatInput');
            if (input) {
                input.value = this.textContent.trim();
                input.focus();
            }
        });
    });


    // Add event delegation for save to log buttons
    document.addEventListener('click', async function(e) {
        if (e.target.classList.contains('save-to-log') || e.target.closest('.save-to-log')) {
            const button = e.target.classList.contains('save-to-log') ? e.target : e.target.closest('.save-to-log');
            const messageContent = button.closest('.message-content');
            const responseText = messageContent.getAttribute('data-content');
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

    // Load chat history when page loads
    loadChatHistory();
});