document.addEventListener("DOMContentLoaded", () => {
const backendURL = "https://taino-heritage-camp-jamaica.onrender.com"; 
const openBtn = document.getElementById("openLightbox");
const closeBtn = document.getElementById("closeLightbox");
const lightbox = document.getElementById("lightbox");
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('nav-links');
const userIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

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

const map = L.map('map').setView([18.4074, -77.1031], 12);

// Add tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const start = [18.4035, -77.0265];
const end   = [18.384744, -76.938089];

// Start & end markers
const startMarker = L.marker(start).addTo(map).bindPopup("Start");
const endMarker = L.marker(end).addTo(map).bindPopup("End");

// Fetch route
fetch(`${backendURL}/route?start=${start[0]},${start[1]}&end=${end[0]},${end[1]}`)
  .then(res => res.json())
  .then(data => {
    console.log("GraphHopper response:", data);

    if (data.paths && data.paths.length > 0) {
      const encoded = data.paths[0].points; // encoded polyline
      const coords = polyline.decode(encoded, 5); // decode with multiplier = 5

      // Draw polyline
      const routeLine = L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);

      // Fit map to route
      map.fitBounds(routeLine.getBounds());

      // Optional: add small pins along the route every N points
      coords.forEach((c, i) => {
        if (i % 20 === 0) { // every 20th point
          L.circleMarker(c, {
            radius: 3,
            color: 'red',
            fillColor: '#f03',
            fillOpacity: 0.7
          }).addTo(map);
        }
      });

      // Optional: make polyline clickable
      routeLine.on('click', () => {
        alert("You clicked the route!");
      });

    } else {
      alert("No route found.");
    }
  })
  .catch(err => console.error("Error fetching route:", err));

let userMarker = null;
let nearestPointMarker = null;

// Function to find nearest route point
function findNearestPoint(latlng, routeCoords) {
  let minDist = Infinity;
  let nearest = null;

  routeCoords.forEach(pt => {
    const dist = map.distance(latlng, pt);
    if (dist < minDist) {
      minDist = dist;
      nearest = pt;
    }
  });

  return nearest;
}

if (navigator.geolocation) {
  navigator.geolocation.watchPosition(
    pos => {
      const userLatLng = [pos.coords.latitude, pos.coords.longitude];

      // Add/update user marker
      if (!userMarker) {
        userMarker = L.marker(userLatLng, { icon: userIcon })
                      .addTo(map)
                      .bindPopup("You are here")
                      .openPopup();
      } else {
        userMarker.setLatLng(userLatLng);
      }

      // Find nearest route point and update marker
      const nearest = findNearestPoint(userLatLng, coords);
      if (!nearestPointMarker) {
        nearestPointMarker = L.circleMarker(nearest, {
          radius: 6,
          color: 'green',
          fillColor: 'lime',
          fillOpacity: 0.8
        }).addTo(map);
      } else {
        nearestPointMarker.setLatLng(nearest);
      }

      // Update completed vs remaining route
      updateRouteProgress(userLatLng);

      // Optionally center map on user
      map.setView(userLatLng, 14);

    },
    err => console.error("Geolocation error:", err),
    { enableHighAccuracy: true, maximumAge: 1000 }
  );
} else {
  alert("Geolocation not supported by your browser.");
}
