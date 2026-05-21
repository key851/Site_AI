document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.doc-card, .level-card, .structure-level');
  cards.forEach((card, index) => {
    card.style.animationDelay = `${Math.min(index * 40, 300)}ms`;
    card.classList.add('fade-in');
  });
});
