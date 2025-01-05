// Handles chat functionality
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('persistentChatForm');
    const chatInput = document.getElementById('persistentChatInput');
    const chatHistory = document.getElementById('chatHistory');
    const chatSidebar = document.getElementById('chatSidebar');

    // Function to add a message to the chat history
    function addMessageToHistory(message, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user' : 'assistant'}`;
        messageDiv.textContent = message;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // Function to mark message as read
    function markMessageAsRead(messageId) {
        fetch('/mark_message_read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message_id: messageId })
        });
    }

    // Handle chat form submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessageToHistory(message, true);
        chatInput.value = '';

        // Send message to server
        fetch('/chat_query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                addMessageToHistory(data.response, false);
                if (data.message_id) {
                    markMessageAsRead(data.message_id);
                }
            } else {
                addMessageToHistory('Error: ' + data.message, false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessageToHistory('Error sending message', false);
        });
    });

    // Initialize chat history from server data
    const initialMessages = document.querySelectorAll('.chat-message');
    initialMessages.forEach(msg => {
        if (!msg.dataset.read) {
            markMessageAsRead(msg.dataset.messageId);
        }
    });
});
