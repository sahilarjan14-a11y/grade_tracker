// ---- tab switching ----

function activateTab(year) {
  document.querySelectorAll(".year-tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => (p.style.display = "none"));

  const tab = document.querySelector(`.year-tab[data-tab="${year}"]`);
  const panel = document.querySelector(`.tab-panel[data-panel="${year}"]`);
  if (tab) tab.classList.add("active");
  if (panel) panel.style.display = "block";
}

// ---- accordion ----

function toggleAccordion(id) {
  const body = document.getElementById("acc-" + id);
  const chev = document.getElementById("chev-" + id);
  if (!body) return;
  const open = body.style.display === "block";
  body.style.display = open ? "none" : "block";
  if (chev) chev.innerHTML = open ? "&#9654;" : "&#9660;";
}

function openAccordion(id) {
  const body = document.getElementById("acc-" + id);
  const chev = document.getElementById("chev-" + id);
  if (body) body.style.display = "block";
  if (chev) chev.innerHTML = "&#9660;";
}

// ---- modal ----

function openEditModal(id, name, weighting, score) {
  document.getElementById("editForm").action = "/assessment/" + id + "/edit";
  document.getElementById("editName").value = name;
  document.getElementById("editWeighting").value = weighting;
  document.getElementById("editScore").value = score;
  document.getElementById("editModal").classList.add("open");
}

function closeEditModal() {
  document.getElementById("editModal").classList.remove("open");
}

// ---- init ----

document.addEventListener("DOMContentLoaded", () => {

  // read ?tab= from url, default to 2
  const params = new URLSearchParams(window.location.search);
  const tab = parseInt(params.get("tab")) || 2;
  activateTab(tab);

  // if there's a #module-N hash, open that accordion
  const hash = window.location.hash;
  const match = hash.match(/^#module-(\d+)$/);
  if (match) {
    const modId = match[1];
    openAccordion(modId);
    // scroll to the card after a brief delay to let display kick in
    setTimeout(() => {
      const el = document.getElementById("module-" + modId);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }

  // wire up tab buttons
  document.querySelectorAll(".year-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      const t = btn.dataset.tab;
      activateTab(t);
      const url = new URL(window.location);
      url.searchParams.set("tab", t);
      url.hash = "";
      window.history.replaceState({}, "", url);
    });
  });

  // wire up accordion triggers
  document.querySelectorAll(".accordion-trigger").forEach(header => {
    header.addEventListener("click", () => {
      const id = header.dataset.target.replace("acc-", "");
      toggleAccordion(id);
    });
  });

  // close modal on overlay click or escape
  const overlay = document.getElementById("editModal");
  if (overlay) {
    overlay.addEventListener("click", e => { if (e.target === overlay) closeEditModal(); });
  }
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeEditModal(); });

  // animate progress bars
  document.querySelectorAll(".progress-fill").forEach(el => {
    const target = el.style.width;
    el.style.width = "0";
    setTimeout(() => { el.style.width = target; }, 120);
  });
});