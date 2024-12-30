document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('scenarioCanvas');
    const elementPalette = document.getElementById('elementPalette');
    const elementProperties = document.getElementById('elementProperties');
    const clearButton = document.getElementById('clearCanvas');
    const saveButton = document.getElementById('saveScenario');
    
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
    
    // Clear and Save buttons
    clearButton.addEventListener('click', clearCanvas);
    saveButton.addEventListener('click', saveScenario);
    
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
            x: x,
            y: y
        });
        
        element.addEventListener('mousedown', handleElementMouseDown);
        element.addEventListener('click', handleElementClick);
    }
    
    function handleElementMouseDown(e) {
        if (e.target.classList.contains('canvas-element')) {
            isDragging = true;
            selectedElement = e.target;
            startX = e.clientX - selectedElement.offsetLeft;
            startY = e.clientY - selectedElement.offsetTop;
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
        selectedElement = null;
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
        
        // Show properties form
        elementProperties.classList.remove('d-none');
        
        // Populate form with element data
        document.getElementById('elementLabel').value = elementData.label;
        document.getElementById('elementDescription').value = elementData.description;
        document.getElementById('elementRiskLevel').value = elementData.riskLevel;
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
        
        // Update visual element
        selectedElementDiv.querySelector('span').textContent = elementData.label;
        selectedElementDiv.dataset.risk = elementData.riskLevel;
    }
    
    function clearCanvas() {
        while (canvas.firstChild) {
            canvas.removeChild(canvas.firstChild);
        }
        elements = [];
        elementProperties.classList.add('d-none');
    }
    
    async function saveScenario() {
        const scenarioData = {
            title: 'New Scenario', // You might want to prompt for this
            elements: elements.map(el => ({
                type: el.type,
                label: el.label,
                description: el.description,
                riskLevel: el.riskLevel,
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
            emergency: 'alert-triangle'
        };
        return icons[type] || 'square';
    }
});
