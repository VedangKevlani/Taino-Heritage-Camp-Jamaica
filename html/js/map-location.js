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

// Initialize map centered between start and destination
const map = L.map('map').setView([18.4035, -77.0265], 12);

// OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Park marker
const parkIcon = L.icon({
    iconUrl: '../images/Taino Heritage Camps logo.jpg', // Replace with your marker image
    iconSize: [30, 30]
});
L.marker([18.384744, -76.938089], {icon: parkIcon})
    .addTo(map)
    .bindPopup("<b>Taino Heritage Camp</b><br>Eden Hill, Oracabessa");

// Routing control
L.Routing.control({
    waypoints: [
        L.latLng(18.4074, -77.1031),   // Start: Ocho Rios Bypass
        L.latLng(18.384744, -76.938089)     // End: Eden Hill, Oracabessa
    ],
    routeWhileDragging: false,
    lineOptions: {
        styles: [{color: 'yellowgreen', weight: 6}]
    },
    createMarker: function(i, wp) {
        let label = i === 0 ? "Start: Ocho Rios" : "Destination: Taino Heritage Camp";
        return L.marker(wp.latLng).bindPopup(label);
    },
    addWaypoints: false,
    position: 'bottomleft'
}).addTo(map);
