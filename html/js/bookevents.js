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

function addMessage(sender, text, clearPrevious=false) {
    if (clearPrevious && sender === "agent") chat.innerHTML = "";
    const div = document.createElement("div");
    div.className = sender === "agent" ? "agent-msg" : "user-msg";
    div.textContent = (sender === "agent" ? "Agent: " : "You: ") + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

//addMessage("agent", data.question, clearPrevious=true);


async function sendAnswer(answer) {
    if (isSending) return; // prevent double send
    isSending = true;
    input.disabled = true;

    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ answer })
        });
        const data = await res.json();

        addMessage("agent", data.question);
        if (!data.done) {
            input.disabled = false;
            input.focus();
        }
    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        console.error(err);
        input.disabled = false;
    } finally {
        isSending = false;
    }
}


input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        btn.click();
    }
});

// Load first question and clear chat
async function loadQuestion() {
    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/ask", {
            credentials: "include"
        });
        const data = await res.json();
        await new Promise(r => setTimeout(r, 2000));
        addMessage("agent", data.question, true); // clearPrevious = true
    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        console.error(err);
    }
}

btn.addEventListener("click", (e) => {
    e.preventDefault();
    const answer = input.value.trim();
    if (!answer || isSending) return; // prevent double submit
    addMessage("user", answer);
    input.value = "";
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

