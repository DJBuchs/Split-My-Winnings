document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.add-rebuy-btn').forEach(function(button) {
        button.addEventListener('click', function() {
            // Find the parent element (the one with the additional-rebuys class)
            const parent = this.closest('.d-flex').nextElementSibling;

            // Create a new div for the additional rebuy input
            const newRebuyDiv = document.createElement('div');
            newRebuyDiv.classList.add('d-flex', 'align-items-center', 'mt-2');

            // Create the new input element
            const newRebuyInput = document.createElement('input');
            newRebuyInput.type = 'number';
            newRebuyInput.classList.add('form-control', 'me-0');
            newRebuyInput.placeholder = 'Rebuy';
            newRebuyInput.required = true;
            newRebuyInput.id = "rebuy_{{ i }}"

            // Add the new input to the new div
            newRebuyDiv.appendChild(newRebuyInput);

            // Optionally add a delete button next to each new rebuy input
            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('btn', 'ms-0');
            deleteBtn.textContent = '✘';
            deleteBtn.type = 'button';

            deleteBtn.addEventListener('click', function() {
                newRebuyDiv.remove(); // Remove the entire div with the input and button
            });

            newRebuyDiv.appendChild(deleteBtn);

            // Append the new rebuy div to the additional rebuy container
            parent.appendChild(newRebuyDiv);
        });
    });
});

