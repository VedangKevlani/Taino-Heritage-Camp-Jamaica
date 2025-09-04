document.addEventListener("DOMContentLoaded", () => {
  const backendURL = "https://taino-heritage-camp-jamaica.onrender.com"; 
  const openBtn = document.getElementById("openLightbox");
  const closeBtn = document.getElementById("closeLightbox");
  const lightbox = document.getElementById("lightbox");
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');
  const startRouteBtn = document.getElementById('startRouteBtn');

  const userIcon = L.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  // Hamburger menu toggle
  hamburger.addEventListener('click', () => {
      navLinks.classList.toggle('active');
  });

  // Lightbox
  openBtn.addEventListener("click", () => lightbox.style.display = "flex");
  closeBtn.addEventListener("click", () => lightbox.style.display = "none");
  lightbox.addEventListener("click", (e) => { if (e.target === lightbox) lightbox.style.display = "none"; });

  // Initialize map at some default location first
  const map = L.map('map').setView([18.4074, -77.1031], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  let coords = null;
  let userMarker = null;
  let nearestPointMarker = null;
  let completedPolyline = null;
  let remainingPolyline = null;

  function findNearestPoint(latlng, routeCoords) {
    let minDist = Infinity;
    let nearest = null;
    routeCoords.forEach(pt => {
      const dist = L.latLng(latlng).distanceTo(L.latLng(pt));
      if (dist < minDist) {
        minDist = dist;
        nearest = pt;
      }
    });
    return nearest;
  }

  function updateRouteProgress(userLatLng) {
    if (!coords) return;
    let minDist = Infinity;
    let nearestIndex = 0;
    coords.forEach((pt, i) => {
      const dist = L.latLng(userLatLng).distanceTo(L.latLng(pt));
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

  function startTrackingRoute() {
    if (!navigator.geolocation) {
      alert("Geolocation not supported by your browser.");
      return;
    }

    navigator.geolocation.getCurrentPosition(pos => {
      const userLatLng = [pos.coords.latitude, pos.coords.longitude];
      map.setView(userLatLng, 14);

      // Place initial user marker
      userMarker = L.marker(userLatLng, { icon: userIcon }).addTo(map).bindPopup("You are here").openPopup();

      // Fetch route starting from user location
      fetch(`${backendURL}/route?start=${userLatLng[0]},${userLatLng[1]}&end=18.384744,-76.938089`)
        .then(res => res.json())
        .then(data => {
          if (data.paths && data.paths.length > 0) {
            coords = polyline.decode(data.paths[0].points, 5);

            // Start & end markers
            L.marker(coords[0]).addTo(map).bindPopup("Start");
            L.marker(coords[coords.length-1]).addTo(map).bindPopup("End");

            // Draw full route
            remainingPolyline = L.polyline(coords, { color: 'blue', weight: 4 }).addTo(map);
            map.fitBounds(remainingPolyline.getBounds());

            // Optional small pins along the route
            coords.forEach((c, i) => {
              if (i % 20 === 0) {
                L.circleMarker(c, { radius: 3, color: 'red', fillColor: '#f03', fillOpacity: 0.7 }).addTo(map);
              }
            });

            // Start watching user position continuously
            navigator.geolocation.watchPosition(pos => {
              const userLatLng = [pos.coords.latitude, pos.coords.longitude];
              userMarker.setLatLng(userLatLng);

              const nearest = findNearestPoint(userLatLng, coords);
              if (!nearestPointMarker) {
                nearestPointMarker = L.circleMarker(nearest, { radius: 6, color: 'green', fillColor: 'lime', fillOpacity: 0.8 }).addTo(map);
              } else {
                nearestPointMarker.setLatLng(nearest);
              }

              updateRouteProgress(userLatLng);
              map.setView(userLatLng, 14);

            }, err => console.error("Geolocation error:", err), { enableHighAccuracy: true, maximumAge: 1000 });
          } else {
            alert("No route found.");
          }
        })
        .catch(err => console.error("Error fetching route:", err));

    }, err => console.error("Initial geolocation error:", err), { enableHighAccuracy: true });
  }

  //startTrackingRoute();
  startRouteBtn.addEventListener('click', () => {
      startTrackingRoute();
  });
});
