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
        document.querySelectorAll('input[type="number"]').forEach(function(input) {
            const storedValue = sessionStorage.getItem(input.id);
            if (storedValue !== null) {
                input.value = storedValue;
            }
        });
    }

    // Load existing data
    loadInputData();

    // Add event listener for input changes
    document.body.addEventListener('input', saveInputData);

    document.querySelectorAll('.add-rebuy-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            const parent = this.closest('.d-flex').nextElementSibling;
            const newRebuyDiv = document.createElement('div');
            newRebuyDiv.classList.add('d-flex', 'align-items-center', 'mt-2');

            const newRebuyInput = document.createElement('input');
            newRebuyInput.type = 'number';
            newRebuyInput.classList.add('form-control', 'me-0');
            newRebuyInput.placeholder = 'Rebuy';
            newRebuyInput.required = true;
            newRebuyInput.step = '50';
            newRebuyInput.id = `rebuy_${Date.now()}`; // Assign a unique ID

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
    });
});