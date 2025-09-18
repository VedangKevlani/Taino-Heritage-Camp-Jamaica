const chat = document.getElementById("chat");
const input = document.getElementById("answer");
const btn = document.getElementById("sendBtn");
let isSending = false;

// ---------------- Lightbox ----------------
const openBtn = document.getElementById("openLightbox");
const closeBtn = document.getElementById("closeLightbox");
const lightbox = document.getElementById("lightbox");

const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');

hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('active');
});

openBtn.addEventListener("click", () => lightbox.style.display = "flex");
closeBtn.addEventListener("click", () => lightbox.style.display = "none");
lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) lightbox.style.display = "none";
});

// ---------------- Chat ----------------
function addMessage(sender, text, clearPrevious=false) {
    if (clearPrevious && sender === "agent") chat.innerHTML = "";
    const div = document.createElement("div");
    div.className = sender === "agent" ? "agent-msg" : "user-msg";
    div.textContent = (sender === "agent" ? "Agent: " : "You: ") + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

// ---------------- Load First Question ----------------
// Load first question (robust)
async function loadQuestion() {
    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/ask", {
            method: "GET",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
        });
        const data = await res.json();
        console.log("First question response:", data);

        if (data.question) {
            addMessage("agent", data.question, true);
            input.disabled = false;
            input.focus();
        } else if (data.message) {
            addMessage("agent", data.message, true);
        } else {
            addMessage("agent", "⚠️ Unexpected response from server.", true);
        }
    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        console.error(err);
    }
}


// Send answer (bulletproof)
async function sendAnswer(answer) {
    if (isSending) return;
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
        console.log("answer response:", data);

        if (data.done) {
            addMessage("agent", data.message || "All questions completed! Thank you.", true);
        } else if (data.question) {
            addMessage("agent", data.question);
            input.disabled = false;
            input.focus();
        } else if (data.message) {
            // fallback where server provided only a message
            addMessage("agent", data.message);
            input.disabled = false;
            input.focus();
        } else {
            addMessage("agent", "⚠️ Unexpected response from server.");
            console.warn("Unexpected server response:", data);
            input.disabled = false;
        }

    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        console.error(err);
        input.disabled = false;
    } finally {
        isSending = false;
    }
}


// ---------------- Input Handling ----------------
input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        btn.click();
    }
});

btn.addEventListener("click", (e) => {
    e.preventDefault();
    const answer = input.value.trim();
    if (!answer || isSending) return;
    addMessage("user", answer);
    input.value = "";
    sendAnswer(answer);
});

// ---------------- Initialize ----------------
document.addEventListener("DOMContentLoaded", () => {
    input.disabled = true; // disable until first question loads
    loadQuestion();
});
