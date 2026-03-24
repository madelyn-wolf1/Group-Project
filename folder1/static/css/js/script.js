// Stock Trader Simulator JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(function(link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});