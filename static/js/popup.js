document.addEventListener("DOMContentLoaded", function () {
    var alertElement = document.getElementById('dataSavedAlert');
    var alert = new bootstrap.Alert(alertElement);
    alertElement.classList.add('show'); // Make alert visible on load
    
    // Automatically close the alert after 3 seconds
    setTimeout(() => {
        alert.close();
    }, 3000);
});