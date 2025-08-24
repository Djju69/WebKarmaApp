document.addEventListener('DOMContentLoaded', function() {
  // QR button functionality
  const qrButtons = document.querySelectorAll('.qr-btn');
  qrButtons.forEach(button => {
    button.addEventListener('click', function() {
      alert('QR-код отсканирован! Скидка применена.');
    });
  });

  // Review button functionality
  const reviewButtons = document.querySelectorAll('.review-btn');
  reviewButtons.forEach(button => {
    button.addEventListener('click', function() {
      alert('Открывается раздел с отзывами...');
    });
  });

  // Language switcher
  const languageButtons = document.querySelectorAll('.language-btn');
  languageButtons.forEach(button => {
    button.addEventListener('click', function() {
      languageButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');
      alert('Язык изменен на: ' + this.textContent);
    });
  });

  // Smooth scrolling for navigation links
  document.querySelectorAll('nav a').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      const targetElement = document.querySelector(targetId);
      if (targetElement) targetElement.scrollIntoView({ behavior: 'smooth' });
    });
  });
});
