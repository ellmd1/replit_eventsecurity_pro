document.addEventListener('DOMContentLoaded', function() {
    let logButton = document.createElement('button');
    logButton.textContent = 'Log Selection';
    logButton.className = 'btn btn-primary position-fixed';
    logButton.style.display = 'none';
    logButton.style.zIndex = '1000';
    document.body.appendChild(logButton);

    // Handle text selection
    document.addEventListener('mouseup', function() {
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
    });

    // Handle logging click
    logButton.addEventListener('click', function() {
        const selectedText = window.getSelection().toString().trim();
        if (selectedText) {
            fetch('/log_selection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: selectedText,
                    source: window.location.pathname
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.getSelection().removeAllRanges();
                    logButton.style.display = 'none';
                    alert('Text logged successfully!');
                }
            })
            .catch(error => {
                console.error('Error logging selection:', error);
                alert('Error logging selection. Please try again.');
            });
        }
    });

    // Hide button when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target !== logButton) {
            logButton.style.display = 'none';
        }
    });
});