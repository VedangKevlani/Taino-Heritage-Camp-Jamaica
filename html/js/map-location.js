document.addEventListener("DOMContentLoaded", () => {
  const backendURL = "https://taino-heritage-camp-jamaica.onrender.com"; 
  const openBtn = document.getElementById("openLightbox");
  const closeBtn = document.getElementById("closeLightbox");
  const lightbox = document.getElementById("lightbox");
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');

  let coords = []; // route coordinates
  let userMarker = null;
  let nearestPointMarker = null;
  let completedPolyline = null;
  let remainingPolyline = null;

  const userIcon = L.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  hamburger.addEventListener('click', () => navLinks.classList.toggle('active'));
  openBtn.addEventListener("click", () => lightbox.style.display = "flex");
  closeBtn.addEventListener("click", () => lightbox.style.display = "none");
  lightbox.addEventListener("click", (e) => { if (e.target === lightbox) lightbox.style.display = "none"; });

  // Function to find nearest point on route
  function findNearestPoint(latlng, routeCoords) {
    let minDist = Infinity;
    let nearest = null;
    routeCoords.forEach(pt => {
      const dist = map.distance(latlng, pt);
      if (dist < minDist) { minDist = dist; nearest = pt; }
    });
    return nearest;
  }

  function updateRouteProgress(userLatLng) {
    if (!coords.length) return;
    let minDist = Infinity;
    let nearestIndex = 0;
    coords.forEach((pt, i) => {
      const dist = map.distance(userLatLng, pt);
      if (dist < minDist) { minDist = dist; nearestIndex = i; }
    });
    const completedCoords = coords.slice(0, nearestIndex + 1);
    const remainingCoordsArr = coords.slice(nearestIndex);
    if (completedPolyline) map.removeLayer(completedPolyline);
    if (remainingPolyline) map.removeLayer(remainingPolyline);
    completedPolyline = L.polyline(completedCoords, { color: 'green', weight: 4 }).addTo(map);
    remainingPolyline = L.polyline(remainingCoordsArr, { color: 'blue', weight: 4 }).addTo(map);
  }

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        const userLatLng = [pos.coords.latitude, pos.coords.longitude];

        // Initialize map at user's location
        const map = L.map('map').setView(userLatLng, 14);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // Start & end points (you can still use fixed end or dynamic)
        const end = [18.384744, -76.938089];
        L.marker(userLatLng, { icon: userIcon }).addTo(map).bindPopup("Start: You are here").openPopup();
        L.marker(end).addTo(map).bindPopup("End");

        // Fetch route from backend
        fetch(`${backendURL}/route?start=${userLatLng[0]},${userLatLng[1]}&end=${end[0]},${end[1]}`)
          .then(res => res.json())
          .then(data => {
            if (data.paths && data.paths.length > 0) {
              coords = polyline.decode(data.paths[0].points, 5);

              const routeLine = L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);
              map.fitBounds(routeLine.getBounds());

              // Optional pins every 20 points
              coords.forEach((c, i) => {
                if (i % 20 === 0) {
                  L.circleMarker(c, { radius: 3, color: 'red', fillColor: '#f03', fillOpacity: 0.7 }).addTo(map);
                }
              });

              // Draw remaining route
              remainingPolyline = L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);
            }
          })
          .catch(err => console.error("Error fetching route:", err));

        // Start watching user position
        navigator.geolocation.watchPosition(
          pos => {
            const userLatLng = [pos.coords.latitude, pos.coords.longitude];
            if (!userMarker) {
              userMarker = L.marker(userLatLng, { icon: userIcon }).addTo(map).bindPopup("You are here").openPopup();
            } else userMarker.setLatLng(userLatLng);

            const nearest = findNearestPoint(userLatLng, coords);
            if (!nearestPointMarker) {
              nearestPointMarker = L.circleMarker(nearest, { radius: 6, color: 'green', fillColor: 'lime', fillOpacity: 0.8 }).addTo(map);
            } else nearestPointMarker.setLatLng(nearest);

            updateRouteProgress(userLatLng);
            map.setView(userLatLng, 14);
          },
          err => console.error("Geolocation error:", err),
          { enableHighAccuracy: true, maximumAge: 1000 }
        );
      },
      err => console.error("Initial geolocation error:", err),
      { enableHighAccuracy: true }
    );
  } else {
    alert("Geolocation not supported by your browser.");
  }
});
