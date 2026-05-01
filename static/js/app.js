function qs(sel) { return document.querySelector(sel); }

function addChatMsg(kind, text) {
  const box = qs("#chatBox");
  if (!box) return;
  const el = document.createElement("div");
  el.className = `chat-msg ${kind}`;
  el.textContent = text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.error || "Request failed");
  return data;
}

window.addEventListener("DOMContentLoaded", () => {
  // Chart
  const chartEl = qs("#riskChart");
  if (chartEl && window.Chart) {
    const labels = window.__chartLabels || [];
    const probs = window.__chartProbs || [];
    new Chart(chartEl, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Risk %",
          data: probs,
          backgroundColor: probs.map((v) => v < 33 ? "rgba(16,185,129,.75)" : (v < 66 ? "rgba(245,158,11,.80)" : "rgba(239,68,68,.78)")),
          borderRadius: 10,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, max: 100 } }
      }
    });
  }

  // Loading animation for prediction
  const form = qs("#predictForm");
  if (form) {
    form.addEventListener("submit", () => {
      const btn = form.querySelector("button[type='submit']");
      if (btn) btn.classList.add("loading");
    });
  }

  // Chatbot
  const chatForm = qs("#chatForm");
  const chatInput = qs("#chatInput");
  if (chatForm && chatInput) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = chatInput.value.trim();
      if (!msg) return;
      chatInput.value = "";
      addChatMsg("me", msg);
      try {
        const data = await postJSON("/api/chat", { message: msg });
        addChatMsg("bot", data.reply || "Thanks for sharing.");
      } catch (err) {
        addChatMsg("bot", "Chat is temporarily unavailable. Please try again.");
      }
    });
  }
});

