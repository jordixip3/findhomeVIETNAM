const CFG = {
  brand: "FindHome Vietnam", currency: "₫",
  mapCenter: [14.0583, 108.2772], mapZoom: 6,
  apiPrefix: window.location.pathname.includes("/VIETNAM") ? "/VIETNAM/api/v1" : "/api/v1"
};

let mainMap = null;

document.addEventListener("DOMContentLoaded", () => {
  initCalc();
  initMap();
  loadProperties();
  initAdmin();
});

function initCalc() {
  const rentInput = document.getElementById("calc-total-rent");
  const roomBtns = document.querySelectorAll(".btn-roommate");
  const resSpan = document.getElementById("calc-per-person");
  const waBtn = document.getElementById("btn-calc-whatsapp");
  let rooms = 4;

  roomBtns.forEach(b => b.addEventListener("click", () => {
    roomBtns.forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    rooms = parseInt(b.dataset.rooms);
    update();
  }));

  rentInput.addEventListener("input", update);

  function update() {
    const r = parseFloat(rentInput.value) || 0;
    const pp = Math.round(r / rooms);
    resSpan.textContent = `${CFG.currency} ${pp.toLocaleString()} / person`;
    waBtn.href = `https://wa.me/34603331391?text=${encodeURIComponent('Hi ' + CFG.brand + ', reserving split of ' + CFG.currency + ' ' + r + ' for ' + rooms + ' roommates.')}`;
  }
  update();
}

function initMap() {
  mainMap = L.map("main-map").setView(CFG.mapCenter, CFG.mapZoom);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(mainMap);
}

async function loadProperties() {
  const grid = document.getElementById("properties-grid");
  const count = document.getElementById("properties-count");
  try {
    const res = await fetch(`${CFG.apiPrefix}/properties`);
    const data = await res.json();
    count.textContent = `${data.length} Available Verified Listings`;
    grid.innerHTML = "";
    data.forEach(p => {
      const d = document.createElement("div");
      d.className = "property-card";
      d.innerHTML = `
        <div class="card-img-container">
          <img src="static/images/prop-mad-01-1.jpg" class="card-img">
          <div class="card-badge">${p.source_portal}</div>
        </div>
        <div class="card-body">
          <div class="card-location">${p.city}, ${p.subdivision}</div>
          <h3 class="card-title">${p.title}</h3>
          <div class="card-pricing">
            <span class="price-split">${CFG.currency} ${p.rent_per_person.toLocaleString()}</span>
            <span class="price-sub">/ person</span>
          </div>
          <div class="card-actions">
            <a href="${p.source_url}" target="_blank" class="btn btn-outline btn-sm">Portal</a>
            <a href="https://wa.me/34603331391?text=${encodeURIComponent('Inquiring about ' + p.title)}" target="_blank" class="btn btn-primary btn-sm">WhatsApp</a>
          </div>
        </div>
      `;
      grid.appendChild(d);
      if (mainMap && p.latitude && p.longitude) {
        L.marker([p.latitude, p.longitude]).addTo(mainMap).bindPopup(`<strong>${p.title}</strong><br>${CFG.currency} ${p.rent_per_person}/person`);
      }
    });
  } catch(e) {
    count.textContent = "Error loading properties.";
  }
}

function initAdmin() {
  const btn = document.getElementById("btn-open-admin");
  const modal = document.getElementById("admin-modal");
  const close = document.getElementById("admin-modal-close");
  const submit = document.getElementById("btn-admin-login-submit");
  const pass = document.getElementById("admin-pass-input");

  btn.addEventListener("click", () => modal.classList.add("active"));
  close.addEventListener("click", () => modal.classList.remove("active"));
  submit.addEventListener("click", async () => {
    if (pass.value === "admin123") {
      document.getElementById("admin-login-view").classList.add("hidden");
      document.getElementById("admin-dashboard-view").classList.remove("hidden");
      const res = await fetch(`${CFG.apiPrefix}/admin/access-logs`);
      const logs = await res.json();
      const tb = document.getElementById("admin-logs-tbody");
      tb.innerHTML = "";
      logs.slice(0, 15).forEach(l => {
        tb.innerHTML += `<tr><td>${l.ip}</td><td>${l.path}</td><td>${l.device_type}</td></tr>`;
      });
    } else { alert("Wrong password"); }
  });
}
