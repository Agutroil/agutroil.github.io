(() => {
  "use strict";

  const database = new URL("./database/", window.location.href);
  const counterRoot = document.getElementById("content-counts");
  const previewRoot = document.getElementById("codex-previews");
  const categories = ["regions", "monsters", "bosses", "dungeons", "items", "equipment", "npcs", "quests", "skills"];
  const labels = { regions: "Regions", monsters: "Monsters", bosses: "Bosses", dungeons: "Dungeons", items: "Items", equipment: "Equipment", npcs: "NPCs", quests: "Quests", skills: "Skills" };
  const selections = [
    ["regions", "world_silverwood"],
    ["monsters", "enemy_briarling"],
    ["monsters", "enemy_rootbound_seer"],
    ["dungeons", "world_moonroot_sanctum"],
    ["equipment", "weapon_warden_blade"],
    ["skills", "skill_power_strike"],
  ];

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]
  );
  const asset = (path) => escapeHtml(new URL(path, database).href);
  const fact = (entry, label) => entry.facts?.find((item) => item.label === label)?.value;

  async function readData(file) {
    const response = await fetch(new URL(`data/${file}.json`, database));
    if (!response.ok) throw new Error("Codex data unavailable");
    return response.json();
  }

  function imageMarkup(entry) {
    const alt = escapeHtml(entry.image_alt || entry.name);
    let image;
    if (entry.image_crop) {
      const [x, y, width, height, sourceWidth, sourceHeight] = entry.image_crop;
      image = `<svg viewBox="${x} ${y} ${width} ${height}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${alt}">
        <image href="${asset(entry.image)}" width="${sourceWidth}" height="${sourceHeight}"></image>
      </svg>`;
    } else {
      image = `<img src="${asset(entry.image)}" alt="${alt}" loading="lazy" decoding="async">`;
    }
    return `<span class="codex-visual is-${escapeHtml(entry.image_kind)}">${image}
      ${entry.image_note ? `<span class="codex-note">${escapeHtml(entry.image_note)}</span>` : ""}
    </span>`;
  }

  function cardMarkup(entry) {
    const isBoss = entry.badges?.some((badge) => badge.label === "Boss");
    const label = isBoss ? "Boss" : ({ region: "Region", monster: "Creature", dungeon: "Dungeon", equipment: "Equipment", skill: "Skill" })[entry.type];
    const description = entry.description || [
      fact(entry, "Biome") || fact(entry, "Archetype"),
      fact(entry, "Levels") ? `Levels ${fact(entry, "Levels")}` : "",
      entry.filters?.region?.[0],
    ].filter(Boolean).join(" · ");
    return `<a class="codex-card" href="./database/#${entry.type}/${encodeURIComponent(entry.id)}">
      ${imageMarkup(entry)}
      <div class="codex-card-body">
        <span class="codex-type">${escapeHtml(label)}</span>
        <h3>${escapeHtml(entry.name)}</h3>
        <p>${escapeHtml(description)}</p>
      </div>
    </a>`;
  }

  async function loadCounters() {
    try {
      const metadata = await readData("metadata");
      counterRoot.innerHTML = categories.map((key) => {
        const category = metadata.categories.find((item) => item.key === key);
        if (!category) return "";
        return `<li><a href="./database/#${key}"><strong>${category.count}</strong><span>${labels[key]}</span></a></li>`;
      }).join("");
      document.getElementById("content-status").textContent = "";
    } catch {
      document.getElementById("content-status").textContent = "Open the Codex to explore the current catalogue.";
    } finally {
      counterRoot.setAttribute("aria-busy", "false");
    }
  }

  async function loadPreviews() {
    try {
      const keys = [...new Set(selections.map(([category]) => category))];
      const payloads = await Promise.all(keys.map(readData));
      const catalogue = Object.fromEntries(keys.map((key, index) => [key, payloads[index].entries]));
      const entries = selections.map(([key, id]) => catalogue[key].find((entry) => entry.id === id)).filter(Boolean);
      previewRoot.innerHTML = entries.map(cardMarkup).join("");
      document.getElementById("codex-status").textContent = "";
    } catch {
      document.getElementById("codex-status").textContent = "Explore the full Codex using the link below.";
    } finally {
      previewRoot.setAttribute("aria-busy", "false");
    }
  }

  loadCounters();
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      loadPreviews();
    }, { rootMargin: "1000px" });
    observer.observe(previewRoot);
  } else {
    loadPreviews();
  }
})();
