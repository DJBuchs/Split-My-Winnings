document.addEventListener('DOMContentLoaded', function() {
    // Function to save input data to sessionStorage
    function saveInputData(event) {
        if (event.target.matches('input')) {
            const key = event.target.id || `rebuy_${Date.now()}`;
            sessionStorage.setItem(key, event.target.value);
            if (!event.target.id) {
                event.target.id = key;
            }
        }
    }

    // Function to load input data from sessionStorage
    function loadInputData() {
        // Loop through all input elements
        document.querySelectorAll('input').forEach(function(input) {
            // Get the stored value from sessionStorage
            const storedValue = sessionStorage.getItem(input.id);
            
            // Check if the stored value exists
            if (storedValue !== null) {
                // Set the value of the input element based on its type
                if (input.type === 'number') {
                    input.value = Number(storedValue); // Convert to number
                } else {
                    input.value = storedValue; // For text or other input types
                }
            }
        });
    }
    

    // Add event listener for input changes
    document.body.addEventListener('input', saveInputData);
    let rowCounter = 0;  // Tracks the current row number

    document.querySelectorAll('.add-rebuy-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const parent = this.closest('.d-flex').nextElementSibling;
            const newRebuyDiv = document.createElement('div');
            newRebuyDiv.classList.add('d-flex', 'align-items-center', 'mt-2');

            const newRebuyInput = document.createElement('input');
            newRebuyInput.type = 'number';
            newRebuyInput.classList.add('form-control', 'me-0');
            newRebuyInput.placeholder = 'Rebuy';
            
            // Use a combination of rowCounter and itemCounter for unique IDs
            const itemCounter = parent.querySelectorAll('input').length + 1; // Number of items in the current row
            newRebuyInput.id = `rebuy_${rowCounter}_${itemCounter}`;

            newRebuyDiv.appendChild(newRebuyInput);

            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('btn', 'ms-0');
            deleteBtn.textContent = '✘';
            deleteBtn.type = 'button';

            deleteBtn.addEventListener('click', function() {
                sessionStorage.removeItem(newRebuyInput.id); // Remove from sessionStorage
                newRebuyDiv.remove();
            });

            newRebuyDiv.appendChild(deleteBtn);
            parent.appendChild(newRebuyDiv);

            // Save the new empty input to sessionStorage
            sessionStorage.setItem(newRebuyInput.id, '');
        });

        rowCounter++;
    });

    // Load existing data
    loadInputData();

});