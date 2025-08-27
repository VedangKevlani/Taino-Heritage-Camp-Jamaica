const chat = document.getElementById("chat");
const input = document.getElementById("answer");
const btn = document.getElementById("sendBtn");
let isSending = false;

const openBtn = document.getElementById("openLightbox");
const closeBtn = document.getElementById("closeLightbox");
const lightbox = document.getElementById("lightbox");

openBtn.addEventListener("click", () => {
  lightbox.style.display = "flex";
});

closeBtn.addEventListener("click", () => {
  lightbox.style.display = "none";
});

lightbox.addEventListener("click", (e) => {
  if (e.target === lightbox) {
    lightbox.style.display = "none";
  }
});

function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "agent" ? "agent-msg" : "user-msg";
    div.textContent = (sender === "agent" ? "Agent: " : "You: ") + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}


async function sendAnswer(answer) {
    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/answer", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ answer })
        });
        const data = await res.json();
        await new Promise(r => setTimeout(r, 2000));
        addMessage("agent", data.question);
        if (!data.done) input.disabled = false;
    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        console.error(err);
        input.disabled = false;
    }
}

async function loadQuestion() {
    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/ask");
        const data = await res.json();
        // 2 sec delay before displaying
        await new Promise(r => setTimeout(r, 2000));
        addMessage("agent", data.question);
    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        console.error(err);
    }
}

btn.addEventListener("click", (e) => {
    e.preventDefault();
    const answer = input.value.trim();
    if (!answer) return;
    addMessage("user", answer);
    input.value = "";
    input.disabled = true;
    sendAnswer(answer);
});

document.addEventListener("DOMContentLoaded", () => {
    loadQuestion();
});

// PDF generation (calls backend /answer route for now)
function generatePDF(ticketData) {
  fetch("https://taino-heritage-camp-jamaica.onrender.com/answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ticketData)
  })
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error("Error generating PDF:", err));
}

