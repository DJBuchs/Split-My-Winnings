document.addEventListener('DOMContentLoaded', function() {
    const contentContainer = document.getElementById('paginated-content');

    function attachPaginationListeners() {
        const paginationLinks = document.querySelectorAll('.pagination .page-link');

        paginationLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const page = this.getAttribute('data-page');
                const url = this.href;

                fetch(url)
                    .then(response => response.text())
                    .then(html => {
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(html, 'text/html');
                        const newContent = doc.getElementById('paginated-content');
                        const newPagination = doc.querySelector('.pagination');

                        contentContainer.innerHTML = newContent.innerHTML;
                        document.querySelector('.pagination').outerHTML = newPagination.outerHTML;

                        // Update URL without refreshing the page
                        history.pushState({page: page}, '', url);

                        // Reattach event listeners to the new pagination links
                        attachPaginationListeners();
                    })
                    .catch(error => console.error('Error:', error));
            });
        });
    }

    // Initial call to attach event listeners
    attachPaginationListeners();
});

