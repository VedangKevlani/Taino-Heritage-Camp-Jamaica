document.addEventListener("DOMContentLoaded", () => {
  const openBtn = document.getElementById("openLightbox");
const closeBtn = document.getElementById("closeLightbox");
const lightbox = document.getElementById("lightbox");
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');

    hamburger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
    });

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

// Initialize map
const map = L.map('map').setView([18.4074, -77.1031], 12);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Example start & end coordinates
const start = [18.4035, -77.0265];
const end   = [18.384744, -76.938089];

// Add markers
L.marker(start).addTo(map).bindPopup("Start");
L.marker(end).addTo(map).bindPopup("End");

// Fetch route from Flask backend
fetch(`/route?start=${start[0]},${start[1]}&end=${end[0]},${end[1]}`)
  .then(res => res.json())
  .then(data => {
    console.log("GraphHopper response:", data);

    if (data.paths && data.paths.length > 0) {
      const points = data.paths[0].points;
      const coords = points.coordinates.map(coord => [coord[1], coord[0]]);
      // GraphHopper: [lng, lat] → Leaflet: [lat, lng]

      // Draw polyline
      L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);

      // Fit bounds
      map.fitBounds(coords);
    } else {
      alert("No route found.");
    }
  })
  .catch(err => console.error("Error fetching route:", err));
});
