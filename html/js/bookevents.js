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

// Add messages to chat
function addMessage(sender, text) {
    const div = document.createElement("div");
    div.className = sender === "agent" ? "agent-msg" : "user-msg";
    div.textContent = sender === "agent" ? "Agent: " + text : "You: " + text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div; // Return the message div for manipulation
}

// Send answer to backend
async function sendAnswer() {
    const answer = input.value.trim();
    if (!answer) return;

    addMessage("user", answer);
    input.value = "";
    input.disabled = true;
    btn.disabled = true;

    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer })
        });
        const data = await res.json();

        // Show "Agent is typing..." message
        const typingDiv = addMessage("agent", "Agent is typing...");

        // Wait 2 seconds
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Replace typing message with actual agent response
        typingDiv.textContent = "Agent: " + data.question;

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
    try {
        const res = await fetch("https://taino-heritage-camp-jamaica.onrender.com/ask");
        const data = await res.json();
        addMessage("agent", data.question);
    } catch (err) {
        console.error("Error fetching first question:", err);
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

// Initialize chat
loadQuestion();
