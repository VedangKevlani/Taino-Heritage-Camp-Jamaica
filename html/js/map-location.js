document.addEventListener("DOMContentLoaded", () => {
  const backendURL = "https://taino-heritage-camp-jamaica.onrender.com"; 
  const openBtn = document.getElementById("openLightbox");
  const closeBtn = document.getElementById("closeLightbox");
  const lightbox = document.getElementById("lightbox");
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');

  // Global variables
  let coords = []; // route coordinates
  let userMarker = null;
  let nearestPointMarker = null;
  let completedPolyline = null;
  let remainingPolyline = null;

  // User icon
  const userIcon = L.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  // Hamburger toggle
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('active');
  });

  // Lightbox open/close
  openBtn.addEventListener("click", () => {
    lightbox.style.display = "flex";
  });
  closeBtn.addEventListener("click", () => {
    lightbox.style.display = "none";
  });
  lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) lightbox.style.display = "none";
  });

  // Initialize map
  const map = L.map('map').setView([18.4074, -77.1031], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  const start = [18.4035, -77.0265];
  const end   = [18.384744, -76.938089];

  // Start & end markers
  L.marker(start).addTo(map).bindPopup("Start");
  L.marker(end).addTo(map).bindPopup("End");

  // Fetch route from backend
  fetch(`${backendURL}/route?start=${start[0]},${start[1]}&end=${end[0]},${end[1]}`)
    .then(res => res.json())
    .then(data => {
      console.log("GraphHopper response:", data);

      if (data.paths && data.paths.length > 0) {
        coords = polyline.decode(data.paths[0].points, 5); // assign globally

        // Draw route
        const routeLine = L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);
        map.fitBounds(routeLine.getBounds());

        // Optional small pins every 20 points
        coords.forEach((c, i) => {
          if (i % 20 === 0) {
            L.circleMarker(c, { radius: 3, color: 'red', fillColor: '#f03', fillOpacity: 0.7 }).addTo(map);
          }
        });

        // Clickable polyline
        routeLine.on('click', () => alert("You clicked the route!"));

        // Draw initial remaining route
        remainingPolyline = L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);
      } else {
        alert("No route found.");
      }
    })
    .catch(err => console.error("Error fetching route:", err));

  // Find nearest point on route
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

  // Update completed vs remaining route
  function updateRouteProgress(userLatLng) {
    if (!coords.length) return;

    let minDist = Infinity;
    let nearestIndex = 0;
    coords.forEach((pt, i) => {
      const dist = map.distance(userLatLng, pt);
      if (dist < minDist) {
        minDist = dist;
        nearestIndex = i;
      }
    });

    const completedCoords = coords.slice(0, nearestIndex + 1);
    const remainingCoords = coords.slice(nearestIndex);

    if (completedPolyline) map.removeLayer(completedPolyline);
    if (remainingPolyline) map.removeLayer(remainingPolyline);

    completedPolyline = L.polyline(completedCoords, { color: 'green', weight: 4 }).addTo(map);
    remainingPolyline = L.polyline(remainingCoords, { color: 'blue', weight: 4 }).addTo(map);
  }

  // Track user position
  if (navigator.geolocation) {
    navigator.geolocation.watchPosition(
      pos => {
        const userLatLng = [pos.coords.latitude, pos.coords.longitude];

        // User marker
        if (!userMarker) {
          userMarker = L.marker(userLatLng, { icon: userIcon })
                        .addTo(map)
                        .bindPopup("You are here")
                        .openPopup();
        } else userMarker.setLatLng(userLatLng);

        // Nearest route point
        const nearest = findNearestPoint(userLatLng, coords);
        if (!nearestPointMarker) {
          nearestPointMarker = L.circleMarker(nearest, {
            radius: 6,
            color: 'green',
            fillColor: 'lime',
            fillOpacity: 0.8
          }).addTo(map);
        } else nearestPointMarker.setLatLng(nearest);

        // Update route progress
        updateRouteProgress(userLatLng);

        // Center map
        map.setView(userLatLng, 14);
      },
      err => console.error("Geolocation error:", err),
      { enableHighAccuracy: true, maximumAge: 1000 }
    );
  } else {
    alert("Geolocation not supported by your browser.");
  }
});
