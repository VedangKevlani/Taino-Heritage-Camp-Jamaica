// events.js

const events = [
  {
    title: "Taino Drumming Workshop",
    date: "2025-09-05",
    description: "Learn the rhythms of our ancestors with a traditional drumming session.",
    image: "../images/taino camp drums.png"
  },
  {
    title: "Herbal Medicine Talk",
    date: "2025-07-10",
    description: "Discover healing plants and their significance in Taino culture.",
    image: "../images/taino camp visitors.jpg"
  },
  {
    title: "Cultural Storytelling",
    date: "2025-10-02",
    description: "An evening of ancestral stories under the sky.",
    image: "../images/taino hill tour.png"
  }
];

const upcomingContainer = document.getElementById("upcoming-events");
const pastContainer = document.getElementById("past-events");
const form = document.getElementById("create-event-form");
const msg = document.getElementById("admin-msg");

const today = new Date();

 const openBtn = document.getElementById("openLightbox");
    const closeBtn = document.getElementById("closeLightbox");
    const lightbox = document.getElementById("lightbox");

//     openBtn.addEventListener("click", () => {
//       lightbox.style.display = "flex"; // show lightbox
//     });

//     closeBtn.addEventListener("click", () => {
//       lightbox.style.display = "none"; // hide lightbox
//     });

//     // Also close if user clicks outside content
//     lightbox.addEventListener("click", (e) => {
//       if (e.target === lightbox) {
//         lightbox.style.display = "none";
//       }
//     });

// // Unified render function
// function renderEvents() {
//   upcomingContainer.innerHTML = "";
//   pastContainer.innerHTML = "";

//   events.forEach((event, index) => {
//     const eventDate = new Date(event.date);
//     const card = document.createElement("div");
//     card.classList.add("event-card");

//     card.innerHTML = `
//       <img src="${event.image}" alt="${event.title}" loading="lazy">
//       <div class="event-info">
//         <h3>${event.title}</h3>
//         <p class="date">${eventDate.toDateString()}</p>
//         <p>${event.description}</p>
//         <button class="btn-delete" data-index="${index}">Delete</button>
//       </div>
//     `;

//     // Append to the correct container
//     if (eventDate >= today) {
//       upcomingContainer.appendChild(card);
//     } else {
//       pastContainer.appendChild(card);
//     }
//   });

//   // Attach delete handlers
//   document.querySelectorAll(".btn-delete").forEach(btn => {
//     btn.addEventListener("click", () => {
//       const idx = btn.dataset.index;
//       events.splice(idx, 1);
//       renderEvents();
//     });
//   });
// }

// // Handle new event creation
// form.addEventListener("submit", (e) => {
//   e.preventDefault();

//   const title = document.getElementById("event-title").value.trim();
//   const date = document.getElementById("event-date").value;
//   const description = document.getElementById("event-description").value.trim();
//   const fileInput = document.getElementById("event-image-file");
//   const file = fileInput.files[0];

//   if (!title || !date || !description || !file) {
//     msg.textContent = "Please fill out all fields!";
//     msg.classList.add("error");
//     return;
//   }

//   const reader = new FileReader();
//   reader.onload = function(event) {
//     const imageSrc = event.target.result;

//     events.push({ title, date, description, image: imageSrc });
//     renderEvents();
//     form.reset();
//     msg.textContent = "Event added successfully!";
//     msg.classList.remove("error");
//   };
//   reader.readAsDataURL(file);
// });

// --- Admin password ---
const adminPassword = "C0k1Yuka600";
const adminSection = document.querySelector(".event-admin");

// Hide admin section by default
adminSection.style.display = "none";

function requestAdminAccess() {
  const pwd = prompt("Enter admin password to manage events:");
  if (pwd === adminPassword) {
    adminSection.style.display = "block"; // show admin section
    msg.textContent = "Admin access granted.";
  } else {
    alert("Incorrect password. Admin features disabled.");
  }
}

// --- Load events from localStorage ---
const savedEvents = localStorage.getItem("events");
if (savedEvents) {
  events.length = 0; // clear default events first
  events.push(...JSON.parse(savedEvents));
}

// --- Save events to localStorage ---
function saveEvents() {
  localStorage.setItem("events", JSON.stringify(events));
}

// --- Render events ---
function renderEvents() {
  upcomingContainer.innerHTML = "";
  pastContainer.innerHTML = "";

  events.forEach((event, index) => {
    const eventDate = new Date(event.date);
    const card = document.createElement("div");
    card.classList.add("event-card");

    card.innerHTML = `
      <img src="${event.image}" alt="${event.title}" loading="lazy">
      <div class="event-info">
        <h3>${event.title}</h3>
        <p class="date">${eventDate.toDateString()}</p>
        <p>${event.description}</p>
        <button class="btn-delete" data-index="${index}">Delete</button>
      </div>
    `;

    if (eventDate >= today) {
      upcomingContainer.appendChild(card);
    } else {
      pastContainer.appendChild(card);
    }
  });

  // Attach delete handlers
  document.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", () => {
      if (adminSection.style.display === "none") {
        alert("Only admins can delete events!");
        return;
      }
      const idx = btn.dataset.index;
      events.splice(idx, 1);
      saveEvents();
      renderEvents();
    });
  });
}

// --- Handle new event creation ---
form.addEventListener("submit", (e) => {
  e.preventDefault();

  if (adminSection.style.display === "none") {
    alert("Only admins can add events!");
    return;
  }

  const title = document.getElementById("event-title").value.trim();
  const date = document.getElementById("event-date").value;
  const description = document.getElementById("event-description").value.trim();
  const fileInput = document.getElementById("event-image-file");
  const file = fileInput.files[0];

  if (!title || !date || !description || !file) {
    msg.textContent = "Please fill out all fields!";
    msg.classList.add("error");
    return;
  }

  const reader = new FileReader();
  reader.onload = function(event) {
    const imageSrc = event.target.result;
    events.push({ title, date, description, image: imageSrc });
    saveEvents();
    renderEvents();
    form.reset();
    msg.textContent = "Event added successfully!";
    msg.classList.remove("error");
  };
  reader.readAsDataURL(file);
});

// --- Lightbox social handlers ---
openBtn.addEventListener("click", () => lightbox.style.display = "flex");
closeBtn.addEventListener("click", () => lightbox.style.display = "none");
lightbox.addEventListener("click", e => {
  if (e.target === lightbox) lightbox.style.display = "none";
});

// --- Initialize ---
renderEvents();
requestAdminAccess();