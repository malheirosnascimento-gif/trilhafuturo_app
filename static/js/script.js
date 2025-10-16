/* === Trilha Futuro - Interatividade e Animações === */

document.addEventListener("DOMContentLoaded", () => {
  
  // --- EFEITOS VISUAIS E ANIMAÇÕES ---

  // 1. Animação de Fade-in para elementos na carga da página
  const fadeInElements = document.querySelectorAll(".fade-in");
  fadeInElements.forEach((element, index) => {
    // Adiciona um pequeno atraso para cada elemento, criando um efeito cascata
    setTimeout(() => {
      element.style.opacity = "1";
      element.style.transform = "translateY(0)";
    }, index * 150);
  });

  // 2. Animação de Reveal para elementos que aparecem durante o scroll
  const revealElements = document.querySelectorAll(".reveal");
  const revealOnScroll = () => {
    revealElements.forEach(element => {
      const elementTop = element.getBoundingClientRect().top;
      const screenHeight = window.innerHeight;
      // Revela o elemento um pouco antes de ele atingir o meio da tela
      if (elementTop < screenHeight - 100) {
        element.classList.add("active");
      }
    });
  };
  
  // Otimiza o evento de scroll para não sobrecarregar o navegador
  window.addEventListener("scroll", revealOnScroll);
  // Executa uma vez na carga para revelar elementos já visíveis
  revealOnScroll();

});