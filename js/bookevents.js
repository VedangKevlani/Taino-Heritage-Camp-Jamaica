const chat = document.getElementById("chat");
const input = document.getElementById("answer");
const btn = document.getElementById("sendBtn");
let isSending = false;

 const openBtn = document.getElementById("openLightbox");
    const closeBtn = document.getElementById("closeLightbox");
    const lightbox = document.getElementById("lightbox");

    openBtn.addEventListener("click", () => {
      lightbox.style.display = "flex"; // show lightbox
    });

    closeBtn.addEventListener("click", () => {
      lightbox.style.display = "none"; // hide lightbox
    });

    // Also close if user clicks outside content
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) {
        lightbox.style.display = "none";
      }
    });
    
// Add messages to chat
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "agent" ? "agent-msg" : "user-msg";
    
    if (sender === "agent") {
        div.textContent = "Agent: " + text;
    } else {
        div.textContent = "You: " + text;
    }

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}


async function sendAnswer() {
    const answer = input.value.trim();
    if (!answer) return;

    addMessage("user", answer);
    input.value = "";
    input.disabled = true;
    btn.disabled = true;

    try {
        const res = await fetch("http://127.0.0.1:5000/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ answer })
        });
        const data = await res.json();
        addMessage("agent", data.question);

        if (!data.done) {
            input.disabled = false;
            btn.disabled = false;
            input.focus();
        }
    } catch (err) {
        addMessage("agent", "Error: Could not reach server.");
        input.disabled = false;
        btn.disabled = false;
    }
}

// Load first question
async function loadQuestion() {
    console.log("DEBUG: loading question...");
    try {
        const res = await fetch("http://127.0.0.1:5000/ask", { credentials: "include" });
        console.log("DEBUG: response status:", res.status);
        const data = await res.json();
        console.log("DEBUG: data received:", data);
        chat.innerHTML += `<div class="agent">${data.question}</div>`;
        chat.scrollTop = chat.scrollHeight;
    } catch (err) {
        console.error("DEBUG: error fetching question:", err);
    }
}


// Event listeners
btn.addEventListener("click", (e) => { e.preventDefault(); sendAnswer(); });
let enterPressed = false;
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !enterPressed) {
    enterPressed = true;
    e.preventDefault();
    sendAnswer().finally(() => { enterPressed = false; });
  }
});

loadQuestion();