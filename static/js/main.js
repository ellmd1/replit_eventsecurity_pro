document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Handle access log form submission
    const accessLogForm = document.getElementById('accessLogForm');
    if (accessLogForm) {
        accessLogForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const reportId = this.dataset.reportId;
            const assessorName = this.elements.assessorName.value;
            const purpose = this.elements.purpose.value;

            try {
                const response = await fetch('/log_access', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        report_id: reportId,
                        assessor_name: assessorName,
                        purpose: purpose
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
