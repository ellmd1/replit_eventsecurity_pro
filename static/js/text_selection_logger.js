// Text Selection Logger
document.addEventListener('DOMContentLoaded', function() {
    let selectionTimeout;
    let logButton = createLogButton();
    document.body.appendChild(logButton);

    // Create floating log button
    function createLogButton() {
        const button = document.createElement('button');
        button.textContent = 'Log Selection';
        button.className = 'btn btn-primary position-fixed';
        button.style.display = 'none';
        button.style.zIndex = '1000';
        button.addEventListener('click', handleLogClick);
        return button;
    }

    // Handle text selection
    document.addEventListener('selectionchange', function() {
        clearTimeout(selectionTimeout);
        selectionTimeout = setTimeout(handleSelection, 200);
    });

    function handleSelection() {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();

        if (selectedText) {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect();

            // Position the button near the selection
            logButton.style.display = 'block';
            logButton.style.top = `${window.scrollY + rect.bottom + 10}px`;
            logButton.style.left = `${window.scrollX + rect.left}px`;
        } else {
            logButton.style.display = 'none';
        }
    }

    // Handle logging click
    function handleLogClick() {
        const selectedText = window.getSelection().toString().trim();
        if (selectedText) {
            const logEntry = {
                text: selectedText,
                timestamp: new Date().toISOString(),
                source: window.location.pathname,
                id: Date.now().toString()
            };

            // Send log entry to server using relative URL
            fetch('/log_selection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(logEntry),
                // Add credentials to ensure cookies are sent
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Clear selection and hide button
                    window.getSelection().removeAllRanges();
                    logButton.style.display = 'none';

                    // Show success message
                    const toast = createToast('Text logged successfully!');
                    document.body.appendChild(toast);
                    setTimeout(() => toast.remove(), 3000);
                }
            })
            .catch(error => {
                console.error('Error logging selection:', error);
                const toast = createToast('Error logging selection. Please try again.');
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 3000);
            });
        }
    }

    // Create toast notification
    function createToast(message) {
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 end-0 p-3';
        toast.style.zIndex = '1100';
        toast.innerHTML = `
            <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <strong class="me-auto">Notification</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        return toast;
    }

    // Hide button when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target !== logButton) {
            logButton.style.display = 'none';
        }
    });
});