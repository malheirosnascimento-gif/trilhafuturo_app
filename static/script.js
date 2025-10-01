/* === Trilha Futuro Digital - Interatividade Revisado === */

document.addEventListener("DOMContentLoaded", () => {
  // Fade-in suave para elementos com classe .fade-in
  const fadeEls = document.querySelectorAll(".fade-in");
  fadeEls.forEach((el, i) => {
    setTimeout(() => {
      el.style.opacity = 1;
      el.style.transform = "translateY(0)";
    }, i * 200);
  });

  // Validar formulários (inputs e textareas)
  const forms = document.querySelectorAll("form");
  forms.forEach(form => {
    form.addEventListener("submit", e => {
      const inputs = form.querySelectorAll("input[required], textarea[required]");
      let valid = true;
      inputs.forEach(input => {
        if (!input.value.trim()) {
          valid = false;
          input.classList.add("input-error");
        } else {
          input.classList.remove("input-error");
        }
      });
      if (!valid) {
        e.preventDefault();
        showToast("⚠️ Preencha todos os campos obrigatórios!", "warning");
      }
    });
  });

  // Chart no dashboard
  if (document.getElementById("statsChart")) {
    fetch("/api/stats")
      .then(res => {
        if (!res.ok) throw new Error("Erro na resposta da API");
        return res.json();
      })
      .then(data => {
        const ctx = document.getElementById("statsChart").getContext("2d");
        new Chart(ctx, {
          type: "doughnut",
          data: {
            labels: ["Criativo", "Analítico", "Equilibrado"],
            datasets: [{
              data: [
                data.criativo || 0,
                data.analitico || 0,
                data.equilibrado || 0
              ],
              backgroundColor: ["#45aaf2", "#fd9644", "#26de81"]
            }]
          },
          options: {
            responsive: true,
            plugins: {
              legend: { position: "bottom" }
            }
          }
        });
      })
      .catch(err => showToast("Erro ao carregar estatísticas!", "warning"));
  }

  // Sistema de pontuação no teste
  const testeForm = document.getElementById("testeForm");
  if (testeForm) {
    testeForm.addEventListener("submit", e => {
      e.preventDefault();
      const respostas = testeForm.querySelectorAll("input[type=radio]:checked");
      let criativo = 0, analitico = 0;
      respostas.forEach(r => {
        if (r.value === "criativo") criativo++;
        else if (r.value === "analitico") analitico++;
      });
      let perfil;
      if (criativo > analitico) perfil = "criativo";
      else if (analitico > criativo) perfil = "analitico";
      else perfil = "equilibrado";
      showToast(`Seu perfil é: ${perfil.toUpperCase()} 🎯`, "success");
      setTimeout(() => {
        testeForm.submit();
      }, 700);
    });
  }
});

// Notificações (toasts)
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 100);
  setTimeout(() => toast.classList.remove("show"), 3500);
  setTimeout(() => toast.remove(), 4000);
}

// Scroll reveal
window.addEventListener("scroll", () => {
  document.querySelectorAll(".reveal").forEach(el => {
    const pos = el.getBoundingClientRect().top;
    const screen = window.innerHeight;
    if (pos < screen - 100) el.classList.add("active");
  });
});

// Estilos de notificação e animações
const style = document.createElement("style");
style.textContent = `
.toast {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%) scale(0.9);
  background: #333;
  color: #fff;
  padding: 12px 18px;
  border-radius: 8px;
  opacity: 0;
  transition: all 0.4s ease;
  z-index: 1000;
  font-weight: 500;
}
.toast.show {
  opacity: 1;
  transform: translateX(-50%) scale(1);
}
.toast.success { background: #26de81; }
.toast.warning { background: #fd9644; }
.toast.info { background: #45aaf2; }
.input-error {
  border-color: #fc5c65 !important;
  background-color: #fff5f5;
}
`;
document.head.appendChild(style);