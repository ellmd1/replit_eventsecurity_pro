document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('scenarioCanvas');
    const elementPalette = document.getElementById('elementPalette');
    const elementProperties = document.getElementById('elementProperties');
    const clearButton = document.getElementById('clearCanvas');
    const totalStaffCountDisplay = document.getElementById('totalStaffCount');
    const overallRiskLevelDisplay = document.getElementById('overallRiskLevel');
    const securityCoverageBar = document.getElementById('securityCoverage');
    const emergencyPointsDisplay = document.getElementById('emergencyPoints');

    let selectedElement = null;
    let elements = [];
    let isDragging = false;
    let startX, startY;

    // Initialize drag events for palette items
    elementPalette.querySelectorAll('.element-item').forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
    });

    // Canvas event listeners
    canvas.addEventListener('dragover', handleDragOver);
    canvas.addEventListener('drop', handleDrop);
    canvas.addEventListener('mousedown', handleCanvasMouseDown);
    canvas.addEventListener('mousemove', handleCanvasMouseMove);
    canvas.addEventListener('mouseup', handleCanvasMouseUp);

    // Clear button
    clearButton.addEventListener('click', clearCanvas);

    // Properties form
    elementProperties.addEventListener('submit', updateElementProperties);

    function handleDragStart(e) {
        e.dataTransfer.setData('text/plain', e.target.dataset.type);
        e.dataTransfer.effectAllowed = 'copy';
    }

    function handleDragEnd(e) {
        e.preventDefault();
    }

    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    }

    function handleDrop(e) {
        e.preventDefault();
        const type = e.dataTransfer.getData('text/plain');
        const rect = canvas.getBoundingClientRect();

        createElement(type, e.clientX - rect.left, e.clientY - rect.top);
        updateScenarioMetrics();
    }

    function createElement(type, x, y) {
        const element = document.createElement('div');
        element.className = 'canvas-element';
        element.dataset.type = type;
        element.dataset.risk = 'Low';
        element.style.left = `${x}px`;
        element.style.top = `${y}px`;

        const icon = document.createElement('i');
        icon.dataset.feather = getIconForType(type);

        const label = document.createElement('span');
        label.textContent = type.charAt(0).toUpperCase() + type.slice(1);

        element.appendChild(icon);
        element.appendChild(label);

        canvas.appendChild(element);
        feather.replace();

        elements.push({
            element: element,
            type: type,
            label: label.textContent,
            description: '',
            riskLevel: 'Low',
            staffCount: 0,
            x: x,
            y: y
        });

        element.addEventListener('mousedown', handleElementMouseDown);
        element.addEventListener('click', handleElementClick);

        updateScenarioMetrics();
    }

    function handleElementMouseDown(e) {
        if (e.target.classList.contains('canvas-element')) {
            isDragging = true;
            selectedElement = e.target;
            startX = e.clientX - selectedElement.offsetLeft;
            startY = e.clientY - selectedElement.offsetTop;
            e.stopPropagation();
        }
    }

    function handleCanvasMouseMove(e) {
        if (isDragging && selectedElement) {
            const x = e.clientX - startX;
            const y = e.clientY - startY;

            selectedElement.style.left = `${x}px`;
            selectedElement.style.top = `${y}px`;

            // Update element position in our data structure
            const elementData = elements.find(el => el.element === selectedElement);
            if (elementData) {
                elementData.x = x;
                elementData.y = y;
            }
        }
    }

    function handleCanvasMouseUp() {
        isDragging = false;
    }

    function handleElementClick(e) {
        const element = e.currentTarget;
        const elementData = elements.find(el => el.element === element);

        // Deselect previously selected element
        document.querySelectorAll('.canvas-element.selected').forEach(el => {
            el.classList.remove('selected');
        });

        // Select clicked element
        element.classList.add('selected');
        selectedElement = element;

        // Show properties form
        elementProperties.classList.remove('d-none');

        // Populate form with element data
        document.getElementById('elementLabel').value = elementData.label;
        document.getElementById('elementDescription').value = elementData.description;
        document.getElementById('elementRiskLevel').value = elementData.riskLevel;
        document.getElementById('elementStaffCount').value = elementData.staffCount;
    }

    function updateElementProperties(e) {
        e.preventDefault();

        const selectedElementDiv = document.querySelector('.canvas-element.selected');
        if (!selectedElementDiv) return;

        const elementData = elements.find(el => el.element === selectedElementDiv);
        if (!elementData) return;

        // Update element data
        elementData.label = document.getElementById('elementLabel').value;
        elementData.description = document.getElementById('elementDescription').value;
        elementData.riskLevel = document.getElementById('elementRiskLevel').value;
        elementData.staffCount = parseInt(document.getElementById('elementStaffCount').value) || 0;

        // Update visual element
        selectedElementDiv.querySelector('span').textContent = elementData.label;
        selectedElementDiv.dataset.risk = elementData.riskLevel;

        updateScenarioMetrics();
    }

    function updateScenarioMetrics() {
        // Update total staff count
        const totalStaff = elements.reduce((sum, el) => sum + (el.staffCount || 0), 0);
        totalStaffCountDisplay.textContent = `Total Staff: ${totalStaff}`;

        // Calculate overall risk level
        const riskLevels = elements.map(el => el.riskLevel);
        let overallRisk = 'Low';
        if (riskLevels.includes('High')) {
            overallRisk = 'High';
        } else if (riskLevels.includes('Medium')) {
            overallRisk = 'Medium';
        }

        overallRiskLevelDisplay.textContent = overallRisk;
        overallRiskLevelDisplay.className = `badge bg-${overallRisk === 'High' ? 'danger' : overallRisk === 'Medium' ? 'warning' : 'success'}`;

        // Calculate security coverage
        const securityElements = elements.filter(el => el.type === 'security').length;
        const totalElements = elements.length;
        const coverage = totalElements > 0 ? (securityElements / totalElements) * 100 : 0;
        securityCoverageBar.style.width = `${coverage}%`;

        // Count emergency response points
        const emergencyPoints = elements.filter(el => 
            el.type === 'emergency' || el.type === 'medical'
        ).length;
        emergencyPointsDisplay.textContent = `${emergencyPoints} points`;
    }

    function clearCanvas() {
        while (canvas.firstChild) {
            canvas.removeChild(canvas.firstChild);
        }
        elements = [];
        elementProperties.classList.add('d-none');
        updateScenarioMetrics();
    }

    async function saveScenarioData() {
        const title = document.getElementById('scenarioTitle').value;
        const description = document.getElementById('scenarioDescription').value;

        if (!title) {
            alert('Please enter a scenario title');
            return;
        }

        const scenarioData = {
            title: title,
            description: description,
            elements: elements.map(el => ({
                type: el.type,
                label: el.label,
                description: el.description,
                riskLevel: el.riskLevel,
                staffCount: el.staffCount,
                x: el.x,
                y: el.y
            }))
        };

        try {
            const response = await fetch('/save_scenario', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(scenarioData)
            });

            const result = await response.json();
            if (result.status === 'success') {
                $('#saveScenarioModal').modal('hide');
                alert('Scenario saved successfully!');
            } else {
                alert('Error saving scenario: ' + result.message);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error saving scenario');
        }
    }

    function getIconForType(type) {
        const icons = {
            venue: 'home',
            entrance: 'log-in',
            security: 'shield',
            crowd: 'users',
            emergency: 'alert-triangle',
            barrier: 'slash',
            medical: 'plus-square'
        };
        return icons[type] || 'square';
    }

    // Make saveScenarioData available globally
    window.saveScenarioData = saveScenarioData;
});