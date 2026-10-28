(() => {
  "use strict";

  const PAGE_SIZE = 12;

  const TYPE_LABEL = {
    item: "Item",
    equipment: "Equipment",
    monster: "Monster",
    boss: "Boss",
    dungeon: "Dungeon",
    region: "Region",
    city: "City",
    npc: "NPC",
    quest: "Quest",
    skill: "Skill",
    resource: "Resource",
    loot: "Loot table",
  };

  const TYPE_TO_CATEGORY = {
    item: "items",
    equipment: "equipment",
    monster: "monsters",
    boss: "bosses",
    dungeon: "dungeons",
    region: "regions",
    city: "cities",
    npc: "npcs",
    quest: "quests",
    skill: "skills",
    resource: "resources",
    loot: "loot",
  };

  const CATEGORY_TYPE = {
    items: "item",
    equipment: "equipment",
    monsters: "monster",
    bosses: "boss",
    dungeons: "dungeon",
    regions: "region",
    cities: "city",
    npcs: "npc",
    quests: "quest",
    skills: "skill",
    resources: "resource",
    loot: "loot",
  };

  const PRIMARY_CATEGORIES = ["items", "monsters", "bosses", "dungeons", "regions", "cities"];
  const SECONDARY_CATEGORIES = ["equipment", "npcs", "quests", "skills", "resources", "loot"];
  const SEARCH_POOL = ["items", "monsters", "dungeons", "regions", "cities", "npcs", "quests", "skills", "resources", "loot"];

  const FILTERS = {
    items: [
      ["category", "Category"],
      ["rarity", "Rarity"],
      ["slot", "Equipment slot"],
    ],
    equipment: [
      ["slot", "Slot"],
      ["rarity", "Rarity"],
      ["category", "Category"],
    ],
    monsters: [
      ["classification", "Classification"],
      ["archetype", "Archetype"],
      ["region", "Found in"],
    ],
    bosses: [["region", "Found in"]],
    dungeons: [
      ["region", "Region"],
      ["boss", "Boss"],
      ["requirement", "Requirement"],
    ],
    regions: [
      ["type", "World type"],
      ["biome", "Biome"],
    ],
    cities: [["region", "Region"]],
    npcs: [
      ["role", "Role"],
      ["location", "Location"],
    ],
    quests: [
      ["turn_in", "Turn in"],
      ["prerequisite", "Prerequisite"],
    ],
    skills: [
      ["type", "Type"],
      ["target", "Target"],
    ],
    resources: [["verb", "Interaction"]],
    loot: [["monster", "Dropped by"]],
  };

  const SORTS = {
    items: [
      ["name-asc", "Name A–Z"],
      ["name-desc", "Name Z–A"],
      ["rarity-desc", "Rarity: high first"],
      ["category-asc", "Category"],
    ],
    equipment: [
      ["name-asc", "Name A–Z"],
      ["name-desc", "Name Z–A"],
      ["rarity-desc", "Rarity: high first"],
      ["category-asc", "Category"],
    ],
    monsters: [
      ["name-asc", "Name A–Z"],
      ["name-desc", "Name Z–A"],
      ["level-asc", "Level: low first"],
    ],
    bosses: [
      ["name-asc", "Name A–Z"],
      ["level-asc", "Level: low first"],
    ],
    dungeons: [
      ["name-asc", "Name A–Z"],
      ["level-asc", "Level: low first"],
    ],
    regions: [
      ["name-asc", "Name A–Z"],
      ["level-asc", "Level: low first"],
    ],
    cities: [["name-asc", "Name A–Z"]],
    npcs: [["name-asc", "Name A–Z"]],
    quests: [["name-asc", "Name A–Z"]],
    skills: [
      ["name-asc", "Name A–Z"],
      ["level-asc", "Required level"],
    ],
    resources: [["name-asc", "Name A–Z"]],
    loot: [["name-asc", "Name A–Z"]],
  };

  const DEFAULT_SORT = Object.fromEntries(
    Object.entries(SORTS).map(([category, options]) => [category, options[0][0]])
  );

  const state = {
    metadata: null,
    data: {},
    byType: {},
    total: 0,
    loaded: false,
    error: null,
    route: { name: "home" },
    activeCategory: null,
    query: "",
    filters: {},
    sort: "name-asc",
    visible: PAGE_SIZE,
    lastSearchResults: [],
    focusOnRender: false,
    scrollOnRender: false,
  };

  const viewRoot = document.getElementById("view-root");
  const searchForm = document.getElementById("search-form");
  const searchInput = document.getElementById("db-search");
  const searchClear = document.getElementById("search-clear");
  const searchStatus = document.getElementById("search-status");
  const catNav = document.getElementById("cat-nav");
  const hero = document.getElementById("hero");

  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (character) => {
      const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
      return map[character];
    });

  const norm = (value) =>
    String(value ?? "")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();

  const plural = (count, singular, pluralForm) =>
    `${count} ${count === 1 ? singular : pluralForm}`;

  const formatDate = (iso) => {
    if (!iso) return "—";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat("en", {
      day: "numeric",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(date);
  };

  const categoryLabel = (key) => {
    const meta = state.metadata?.categories.find((category) => category.key === key);
    return meta?.label || key;
  };

  const categoryMeta = (key) =>
    state.metadata?.categories.find((category) => category.key === key) || null;

  function parseRoute() {
    const raw = window.location.hash.replace(/^#\/?/, "");
    if (!raw || raw === "top") return { name: "home" };
    if (raw === "search") return { name: "search" };
    if (raw.includes("/")) {
      const [type, ...rest] = raw.split("/");
      const id = decodeURIComponent(rest.join("/"));
      if (TYPE_TO_CATEGORY[type] && id) {
        return { name: "detail", type, id, category: TYPE_TO_CATEGORY[type] };
      }
    }
    if (CATEGORY_TYPE[raw]) {
      return { name: "category", category: raw };
    }
    return { name: "notfound", raw };
  }

  function routeKey(route) {
    if (route.name === "detail") return `detail:${route.type}:${route.id}`;
    if (route.name === "category") return `category:${route.category}`;
    return route.name;
  }

  function resetCategoryState(category) {
    state.filters = {};
    state.sort = DEFAULT_SORT[category] || "name-asc";
    state.visible = PAGE_SIZE;
  }

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) {
      throw new Error(`${path} returned ${response.status}`);
    }
    return response.json();
  }

  async function loadData() {
    state.loaded = false;
    state.error = null;
    viewRoot.setAttribute("aria-busy", "true");
    viewRoot.innerHTML = `
      <div class="loading-panel" role="status">
        <span class="loading-rune" aria-hidden="true">✦</span>
        <p>Reading the Nythara codex…</p>
      </div>`;
    searchStatus.textContent = "Loading the codex…";

    try {
      const metadata = await fetchJson("data/metadata.json");
      const payloads = await Promise.all(
        metadata.categories.map((category) => fetchJson(`data/${category.key}.json`))
      );

      state.metadata = metadata;
      state.data = {};
      state.byType = {};
      metadata.categories.forEach((category, index) => {
        const payload = payloads[index];
        state.data[category.key] = payload;
        const type = CATEGORY_TYPE[category.key];
        state.byType[type] = new Map(payload.entries.map((entry) => [entry.id, entry]));
        payload.entries.forEach((entry) => {
          entry.__search = norm(
            [
              entry.name,
              entry.id,
              entry.subtitle,
              entry.description || "",
              ...(entry.facts || []).flatMap((fact) => [fact.label, fact.value]),
              ...(entry.badges || []).map((badge) => badge.label),
              ...Object.values(entry.filters || {}).flat(),
              ...(entry.sections || []).flatMap((section) => [
                section.title,
                ...(section.facts || []).flatMap((fact) => [fact.label, fact.value]),
                ...(section.links || []).flatMap((link) => [link.name, link.meta || "", TYPE_LABEL[link.type] || link.type]),
              ]),
            ].join(" ")
          );
          entry.__name = norm(entry.name);
          entry.__subtitle = norm(entry.subtitle);
          entry.__id = norm(entry.id);
        });
      });

      state.total = metadata.total_primary_entries;
      state.loaded = true;
      fillSnapshot();
      searchStatus.textContent = `${state.total} entries across ${metadata.categories.length} categories`;
      render({ focus: false });
      viewRoot.setAttribute("aria-busy", "false");
    } catch (error) {
      console.error(error);
      state.error = error;
      state.loaded = false;
      viewRoot.setAttribute("aria-busy", "false");
      renderError();
    }
  }

  function fillSnapshot() {
    if (!state.metadata) return;
    const meta = state.metadata;
    const count = document.getElementById("snapshot-count");
    const source = document.getElementById("snapshot-source");
    const categories = document.getElementById("snapshot-categories");
    const generated = document.getElementById("snapshot-generated");
    const footerSource = document.getElementById("footer-source");
    if (count) count.textContent = String(meta.total_primary_entries);
    if (source) {
      source.textContent = meta.source_short_commit;
    }
    if (categories) categories.textContent = String(meta.categories.length);
    if (generated) generated.textContent = formatDate(meta.generated_at);
    if (footerSource) {
      footerSource.textContent = `Game data · ${meta.source_ref} @ ${meta.source_short_commit}`;
    }
  }

  function renderError() {
    document.body.dataset.view = "notfound";
    document.title = "Database unavailable · Nythara";
    searchStatus.textContent = "The codex could not be loaded.";
    viewRoot.innerHTML = `
      <div class="message-panel message-panel--error" role="alert">
        <p class="eyebrow">Database unavailable</p>
        <h2>The Nythara database could not be loaded.</h2>
        <p>
          The generated game data could not be read. This is a static snapshot, so
          a missing or blocked JSON file is enough to stop the catalogue.
        </p>
        <div class="button-row">
          <button class="button" type="button" data-retry>Try again</button>
          <a class="button button--ghost" href="../">Back to the Nythara page</a>
        </div>
      </div>`;
  }

  function setStatus(html) {
    searchStatus.innerHTML = html;
  }

  function setDocumentMeta(route) {
    if (route.name === "detail") {
      const entry = getEntry(route.type, route.id);
      if (entry) {
        document.title = `${entry.name} · ${TYPE_LABEL[entry.type]} · Nythara Database`;
        return;
      }
    }
    if (route.name === "category") {
      document.title = `${categoryLabel(route.category)} · Nythara Database`;
      return;
    }
    if (route.name === "search") {
      document.title = "Search · Nythara Database";
      return;
    }
    document.title = "Nythara Database | Items, Monsters, Dungeons & World";
  }

  function getEntry(type, id) {
    return state.byType[type]?.get(id) || null;
  }

  function updateNav() {
    const active =
      state.route.name === "category"
        ? state.route.category
        : state.route.name === "detail"
          ? state.route.category
          : null;
    catNav.querySelectorAll("a").forEach((link) => {
      if (link.dataset.cat === active) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  }

  function mediaType(type) {
    if (["region", "dungeon", "city", "boss"].includes(type)) return "is-art";
    if (type === "monster") return "is-sprite";
    return "is-icon";
  }

  function mediaMarkup(entry, detail = false) {
    const base = detail ? "detail-media" : "entry-media";
    const layout = mediaType(entry.type);
    const classes = [base, layout, entry.image ? "" : "is-rune"].filter(Boolean).join(" ");
    if (!entry.image) {
      return `<div class="${classes}"><span class="media-rune" aria-hidden="true">✦</span></div>`;
    }
    const loading = detail ? "" : ' loading="lazy"';
    return `<div class="${classes}">
      <img src="${escapeHtml(entry.image)}" alt="${escapeHtml(entry.image_alt || entry.name)}" decoding="async"${loading}>
    </div>`;
  }

  function badgeMarkup(badges) {
    return `<div class="badges">${(badges || [])
      .map((badge) => `<span class="badge tone-${escapeHtml(badge.tone || "muted")}">${escapeHtml(badge.label)}</span>`)
      .join("")}</div>`;
  }

  function factRows(facts) {
    return `<div class="fact-list">${facts
      .map(
        (fact) => `<div class="fact-row">
          <dt>${escapeHtml(fact.label)}</dt>
          <dd>${escapeHtml(fact.value)}</dd>
        </div>`
      )
      .join("")}</div>`;
  }

  function factGrid(facts) {
    return `<dl class="facts-grid">${facts
      .map(
        (fact) => `<div class="fact">
          <dt>${escapeHtml(fact.label)}</dt>
          <dd>${escapeHtml(fact.value)}</dd>
        </div>`
      )
      .join("")}</dl>`;
  }

  function linksMarkup(links) {
    return `<div class="link-list">${links
      .map((link) => {
        const label = TYPE_LABEL[link.type] || link.type;
        return `<a class="entity-link" href="#${escapeHtml(link.type)}/${encodeURIComponent(link.id)}">
          <span class="entity-type">${escapeHtml(label)}</span>
          <strong>${escapeHtml(link.name)}</strong>
          ${link.meta ? `<span class="entity-meta">${escapeHtml(link.meta)}</span>` : ""}
        </a>`;
      })
      .join("")}</div>`;
  }

  function cardFacts(entry) {
    return (entry.facts || [])
      .filter((fact) => fact.label !== "Stable ID")
      .slice(0, 3)
      .map(
        (fact) => `<div class="entry-fact">
          <span>${escapeHtml(fact.label)}</span>
          <strong>${escapeHtml(fact.value)}</strong>
        </div>`
      )
      .join("");
  }

  function entryCard(entry) {
    return `<a class="entry-card" data-type="${escapeHtml(entry.type)}" href="#${escapeHtml(
      entry.type
    )}/${encodeURIComponent(entry.id)}">
      ${mediaMarkup(entry)}
      <div class="entry-body">
        <span class="entry-type">${escapeHtml(TYPE_LABEL[entry.type] || entry.type)}</span>
        <span class="entry-name">${escapeHtml(entry.name)}</span>
        ${entry.subtitle ? `<span class="entry-subtitle">${escapeHtml(entry.subtitle)}</span>` : ""}
        ${entry.badges?.length ? badgeMarkup(entry.badges.slice(0, 3)) : ""}
        ${cardFacts(entry) ? `<div class="entry-facts">${cardFacts(entry)}</div>` : ""}
      </div>
    </a>`;
  }

  function categoryCard(category, primary) {
    const icon = category.key;
    return `<a class="category-card${primary ? " category-card--primary" : ""}" href="#${escapeHtml(category.key)}">
      <span class="category-arrow" aria-hidden="true">↗</span>
      <span class="category-icon"><svg class="icon" aria-hidden="true"><use href="#i-${escapeHtml(
        icon
      )}"></use></svg></span>
      <span class="category-label">${escapeHtml(category.label)}</span>
      <span class="category-count">${plural(category.count, "entry", "entries")}</span>
      <span class="category-desc">${escapeHtml(category.description)}</span>
    </a>`;
  }

  function renderHome() {
    const meta = state.metadata;
    const primary = PRIMARY_CATEGORIES.map(categoryMeta).filter(Boolean);
    const secondary = SECONDARY_CATEGORIES.map(categoryMeta).filter(Boolean);
    viewRoot.innerHTML = `
      <div class="home-intro">
        <div>
          <p class="eyebrow">Browse the codex</p>
          <h2 tabindex="-1">Every real entry, one place.</h2>
          <p>
            Search the full catalogue or step through items, creatures, dungeons,
            regions and the systems that connect them. Every count below is read
            from the generated game data, not typed by hand.
          </p>
        </div>
        <span class="home-total"><strong>${state.total}</strong> primary entries</span>
      </div>

      <div class="category-group">
        <div class="group-head"><h3>Core catalogue</h3></div>
        <div class="category-grid category-grid--primary">
          ${primary.map((category) => categoryCard(category, true)).join("")}
        </div>
      </div>

      <div class="category-group">
        <div class="group-head"><h3>Systems &amp; support</h3></div>
        <div class="category-grid">
          ${secondary.map((category) => categoryCard(category, false)).join("")}
        </div>
      </div>

      <div class="codex-notes">
        <article class="note-card">
          <span>Source of truth</span>
          <h3>Read from Nythara</h3>
          <p>
            Parsed from the authored Godot resources and WorldGraph at
            <span class="mono">${escapeHtml(meta.source_ref)} @ ${escapeHtml(
              meta.source_short_commit
            )}</span>.
          </p>
        </article>
        <article class="note-card">
          <span>Static by design</span>
          <h3>No live backend</h3>
          <p>
            GitHub Pages serves a generated snapshot. Item stats, encounters and
            loot are never fetched from a game server here.
          </p>
        </article>
        <article class="note-card">
          <span>Scope</span>
          <h3>Public main only</h3>
          <p>
            Unmerged development branches, including in-progress online work, are
            not represented in this codex.
          </p>
        </article>
      </div>`;

    setStatus(
      `<strong>${state.total}</strong> entries across <strong>${meta.categories.length}</strong> categories · search by name, stable ID, region or item`
    );
  }

  function visibleEntries(entries) {
    const filtered = entries.filter((entry) => {
      return Object.entries(state.filters).every(([field, value]) => {
        if (!value) return true;
        const entryValue = entry.filters?.[field];
        if (Array.isArray(entryValue)) return entryValue.includes(value);
        return entryValue === value;
      });
    });

    const [key, direction] = state.sort.split("-");
    const ordered = [...filtered].sort((a, b) => {
      if (key === "name") return a.sort.name.localeCompare(b.sort.name);
      if (key === "level") return (a.sort.level || 0) - (b.sort.level || 0);
      if (key === "rarity") return (a.sort.rarity || 0) - (b.sort.rarity || 0);
      if (key === "category") return String(a.sort.category).localeCompare(String(b.sort.category));
      return 0;
    });
    if (direction === "desc") ordered.reverse();
    return ordered;
  }

  function buildFilters(entries, category) {
    const definitions = FILTERS[category] || [];
    return definitions
      .map(([field, label]) => {
        const values = new Set();
        entries.forEach((entry) => {
          const value = entry.filters?.[field];
          if (Array.isArray(value)) value.forEach((item) => item && values.add(String(item)));
          else if (value) values.add(String(value));
        });
        if (values.size < 2) return null;
        return { field, label, values: [...values].sort((a, b) => a.localeCompare(b)) };
      })
      .filter(Boolean);
  }

  function filtersMarkup(filters, activeCount) {
    return `<details class="filter-panel" open>
      <summary>
        <span>Filters${activeCount ? ` · ${activeCount} active` : ""}</span>
        <svg class="icon" aria-hidden="true"><use href="#i-chevron"></use></svg>
      </summary>
      <div class="filter-body">
        ${filters
          .map(
            ({ field, label, values }) => `<div class="filter-group">
              <label for="filter-${escapeHtml(field)}">${escapeHtml(label)}</label>
              <select id="filter-${escapeHtml(field)}" data-filter="${escapeHtml(field)}">
                <option value="">All</option>
                ${values
                  .map(
                    (value) => `<option value="${escapeHtml(value)}"${
                      state.filters[field] === value ? " selected" : ""
                    }>${escapeHtml(value)}</option>`
                  )
                  .join("")}
              </select>
            </div>`
          )
          .join("")}
        ${
          activeCount
            ? `<button class="filter-reset" type="button" data-reset-filters>Clear filters</button>`
            : ""
        }
      </div>
    </details>`;
  }

  function sortMarkup(category) {
    const options = SORTS[category] || SORTS.items;
    if (options.length < 2) return "";
    return `<label class="sort-control">
      <span>Sort</span>
      <select id="sort-select">
        ${options
          .map(
            ([value, label]) =>
              `<option value="${escapeHtml(value)}"${state.sort === value ? " selected" : ""}>${escapeHtml(
                label
              )}</option>`
          )
          .join("")}
      </select>
    </label>`;
  }

  function resultsMarkup(entries, total) {
    const visible = entries.slice(0, state.visible);
    return `<div class="entry-grid" id="entry-grid">
        ${visible.map(entryCard).join("")}
      </div>
      ${
        entries.length > state.visible
          ? `<div class="load-more-wrap">
              <button class="load-more" type="button" data-load-more>
                Load ${Math.min(PAGE_SIZE, entries.length - state.visible)} more
              </button>
            </div>`
          : ""
      }
      ${
        entries.length === 0
          ? `<div class="empty-state">
              <h3>No entries match these filters.</h3>
              <p>Try a different filter or clear the current selection.</p>
              <button class="button button--ghost" type="button" data-reset-filters>Clear filters</button>
            </div>`
          : ""
      }
      <p class="sr-only" role="status" aria-live="polite">${visible.length} of ${entries.length} entries shown.</p>`;
  }

  function renderCategory() {
    const category = state.route.category;
    const meta = state.metadata.categories.find((item) => item.key === category);
    const payload = state.data[category];
    if (!meta || !payload) {
      renderNotFound();
      return;
    }
    if (state.activeCategory !== category) {
      resetCategoryState(category);
      state.activeCategory = category;
    }
    const entries = visibleEntries(payload.entries);
    const filters = buildFilters(payload.entries, category);
    const activeCount = Object.values(state.filters).filter(Boolean).length;
    const primary = PRIMARY_CATEGORIES.includes(category);

    viewRoot.innerHTML = `
      <div class="view-head">
        <nav class="crumbs" aria-label="Breadcrumb">
          <a href="#">Database</a><span class="sep">/</span>
          <span aria-current="page">${escapeHtml(meta.label)}</span>
        </nav>
        <div class="view-title-row">
          <div>
            <p class="eyebrow">${primary ? "Core catalogue" : "Systems &amp; support"}</p>
            <h2 tabindex="-1">${escapeHtml(meta.label)}</h2>
            <p class="view-desc">${escapeHtml(meta.description)}</p>
          </div>
          <div class="view-meta"><strong>${payload.count}</strong><span>entries</span></div>
        </div>
      </div>

      <div class="explorer-layout${filters.length ? "" : " explorer-layout--plain"}">
        ${
          filters.length
            ? `<aside class="filters-col">${filtersMarkup(filters, activeCount)}</aside>`
            : ""
        }
        <div class="results-col">
          <div class="results-toolbar">
            <p class="results-count" id="results-count" tabindex="-1"><strong>${entries.length}</strong> of ${payload.count} ${payload.count === 1 ? "entry" : "entries"}</p>
            ${sortMarkup(category)}
          </div>
          ${resultsMarkup(entries, payload.count)}
        </div>
      </div>`;

    setStatus(
      `<strong>${entries.length}</strong> of ${payload.count} ${payload.count === 1 ? "entry" : "entries"} in ${escapeHtml(meta.label)}${activeCount ? ` · ${activeCount} ${activeCount === 1 ? "filter" : "filters"} active` : ""}`
    );
  }

  function searchScore(entry, query, tokens) {
    if (!tokens.every((token) => entry.__search.includes(token))) return 0;
    let score = 0;
    if (entry.__name === query) score += 200;
    else if (entry.__name.startsWith(query)) score += 120;
    else if (entry.__name.includes(query)) score += 80;
    if (entry.__id.includes(query)) score += 40;
    if (entry.__subtitle.includes(query)) score += 20;
    tokens.forEach((token) => {
      if (entry.__name.includes(token)) score += 8;
    });
    return score;
  }

  function searchResults(query) {
    const normalized = norm(query).trim();
    if (!normalized) return [];
    const tokens = normalized.split(/\s+/).filter(Boolean);
    const results = [];
    SEARCH_POOL.forEach((category) => {
      state.data[category]?.entries.forEach((entry) => {
        const score = searchScore(entry, normalized, tokens);
        if (score > 0) results.push({ entry, score });
      });
    });
    results.sort((a, b) => b.score - a.score || a.entry.sort.name.localeCompare(b.entry.sort.name));
    return results;
  }

  function renderSearch() {
    const query = state.query.trim();
    if (!query) {
      viewRoot.innerHTML = `
        <div class="view-head">
          <nav class="crumbs" aria-label="Breadcrumb">
            <a href="#">Database</a><span class="sep">/</span>
            <span aria-current="page">Search</span>
          </nav>
          <h2 tabindex="-1">Search the codex</h2>
          <p class="view-desc">Find an item, creature, dungeon, region, NPC, quest or skill by name or stable ID.</p>
        </div>
        <div class="message-panel">
          <p class="eyebrow">Global search</p>
          <h2>Start typing in the field above.</h2>
          <p>Try a creature, a piece of gear, a dungeon or a place.</p>
          <div class="button-row">
            ${["Briarling", "Warden Blade", "Moonroot Sanctum", "Silverwood", "Rootbound Seer"]
              .map((term) => `<button class="hint" type="button" data-search="${escapeHtml(term)}">${escapeHtml(term)}</button>`)
              .join("")}
          </div>
        </div>`;
      setStatus("Type to search the database.");
      state.lastSearchResults = [];
      return;
    }

    const results = searchResults(query);
    state.lastSearchResults = results.map((result) => result.entry);
    const entries = state.lastSearchResults.slice(0, state.visible);
    viewRoot.innerHTML = `
      <div class="view-head">
        <nav class="crumbs" aria-label="Breadcrumb">
          <a href="#">Database</a><span class="sep">/</span>
          <span aria-current="page">Search</span>
        </nav>
        <div class="view-title-row">
          <div>
            <p class="eyebrow">Search results</p>
            <h2 tabindex="-1">“${escapeHtml(query)}”</h2>
            <p class="view-desc">${results.length ? `${plural(results.length, "entry", "entries")} matched across the codex.` : "No entries matched this search."}</p>
          </div>
          <div class="view-meta"><strong>${results.length}</strong><span>matches</span></div>
        </div>
      </div>
      ${
        results.length
          ? `<div class="results-toolbar">
              <p class="results-count" id="results-count" tabindex="-1"><strong>${entries.length}</strong> of ${results.length} shown</p>
            </div>
            ${resultsMarkup(state.lastSearchResults, results.length)}`
          : `<div class="empty-state">
              <h3>No entries match “${escapeHtml(query)}”.</h3>
              <p>Try a shorter term, a stable ID or a location.</p>
              <button class="button button--ghost" type="button" data-clear-search>Clear search</button>
            </div>`
      }`;

    setStatus(
      results.length
        ? `<strong>${results.length}</strong> ${results.length === 1 ? "match" : "matches"} for “${escapeHtml(query)}”`
        : `No matches for “${escapeHtml(query)}”`
    );
  }

  function renderDetail() {
    const entry = getEntry(state.route.type, state.route.id);
    if (!entry) {
      renderNotFound("That entry does not exist in the generated codex.");
      return;
    }
    const category = state.route.category;
    const meta = categoryMeta(category);
    const source = state.metadata;
    const backHref = `#${category}`;

    viewRoot.innerHTML = `
      <div class="detail">
        <nav class="crumbs" aria-label="Breadcrumb">
          <a href="#">Database</a><span class="sep">/</span>
          <a href="${backHref}">${escapeHtml(meta?.label || category)}</a><span class="sep">/</span>
          <span aria-current="page">${escapeHtml(entry.name)}</span>
        </nav>
        <a class="back-link" href="${backHref}">
          <svg class="icon" aria-hidden="true"><use href="#i-arrow"></use></svg>
          Back to ${escapeHtml(meta?.label || category)}
        </a>

        <article class="detail-record" data-type="${escapeHtml(entry.type)}">
          <header class="detail-hero">
            ${mediaMarkup(entry, true)}
            <div class="detail-copy">
              <p class="eyebrow">${escapeHtml(TYPE_LABEL[entry.type] || entry.type)} entry</p>
              <h2 tabindex="-1">${escapeHtml(entry.name)}</h2>
              ${entry.subtitle ? `<p class="detail-subtitle">${escapeHtml(entry.subtitle)}</p>` : ""}
              ${entry.badges?.length ? badgeMarkup(entry.badges) : ""}
              ${entry.description ? `<p class="detail-description">${escapeHtml(entry.description)}</p>` : ""}
            </div>
          </header>

          ${entry.facts?.length ? `<section class="facts-block" aria-labelledby="facts-title">
            <h3 id="facts-title">Data</h3>
            ${factGrid(entry.facts)}
          </section>` : ""}

          ${(entry.sections || [])
            .filter((section) => section.facts?.length || section.links?.length)
            .map(
              (section, index) => `<section class="detail-section" aria-labelledby="section-${index}">
                <h3 id="section-${index}">${escapeHtml(section.title)}</h3>
                ${section.facts?.length ? factRows(section.facts) : ""}
                ${section.links?.length ? linksMarkup(section.links) : ""}
              </section>`
            )
            .join("")}

          <p class="detail-source">
            Source: Nythara ${escapeHtml(source.source_ref)} @ ${escapeHtml(
              source.source_short_commit
            )} · ${escapeHtml(
              TYPE_LABEL[entry.type] || entry.type
            )} <code>${escapeHtml(entry.id)}</code> · generated ${escapeHtml(
              formatDate(source.generated_at)
            )}. Static snapshot, not a live server feed.
          </p>
        </article>
      </div>`;

    setStatus(
      `Viewing <strong>${escapeHtml(entry.name)}</strong> · ${escapeHtml(
        TYPE_LABEL[entry.type] || entry.type
      )} · game data ${escapeHtml(source.source_short_commit)}`
    );
  }

  function renderNotFound(message = "") {
    document.body.dataset.view = "notfound";
    viewRoot.innerHTML = `
      <div class="message-panel">
        <p class="eyebrow">Not in the codex</p>
        <h2>This page is not part of the Nythara Database.</h2>
        <p>${escapeHtml(message || "The address does not match one of the generated entries.")}</p>
        <div class="button-row">
          <a class="button" href="#">Back to the database</a>
          <a class="button button--ghost" href="../">Nythara project page</a>
        </div>
      </div>`;
    setStatus("Entry not found.");
  }

  function render({ focus = false } = {}) {
    if (!state.loaded) {
      if (state.error) renderError();
      return;
    }

    updateNav();
    setDocumentMeta(state.route);
    document.body.dataset.view = state.route.name;

    if (state.route.name === "home") {
      renderHome();
    } else if (state.route.name === "category") {
      renderCategory();
    } else if (state.route.name === "search") {
      renderSearch();
    } else if (state.route.name === "detail") {
      renderDetail();
    } else {
      renderNotFound();
    }

    viewRoot.setAttribute("aria-busy", "false");

    if (focus) {
      const heading = viewRoot.querySelector("h2[tabindex='-1']");
      if (heading) {
        heading.focus({ preventScroll: true });
      }
    }
  }

  function updateSearchChrome() {
    searchClear.hidden = !state.query;
  }

  function showSearch(term) {
    state.query = term;
    searchInput.value = term;
    updateSearchChrome();
    if (window.location.hash !== "#search") {
      history.pushState(null, "", `${window.location.pathname}${window.location.search}#search`);
    }
    state.route = { name: "search" };
    state.visible = PAGE_SIZE;
    render({ focus: true });
  }

  function clearSearch() {
    state.query = "";
    searchInput.value = "";
    updateSearchChrome();
    if (state.route.name === "search") {
      history.replaceState(null, "", window.location.pathname + window.location.search);
      state.route = { name: "home" };
      state.activeCategory = null;
      render({ focus: true });
    } else {
      setStatus(`${state.total} entries across ${state.metadata?.categories.length || 0} categories`);
      searchInput.focus();
    }
  }

  function onHashChange() {
    const nextRoute = parseRoute();
    const previousRoute = state.route;
    const previousKey = routeKey(previousRoute);
    const nextKey = routeKey(nextRoute);
    state.route = nextRoute;

    if (nextRoute.name === "category") {
      if (state.activeCategory !== nextRoute.category) {
        resetCategoryState(nextRoute.category);
        state.activeCategory = nextRoute.category;
      }
    } else if (nextRoute.name === "home") {
      state.activeCategory = null;
    }

    if (nextRoute.name === "category" || nextRoute.name === "home") {
      state.query = "";
      searchInput.value = "";
      updateSearchChrome();
    }

    if (nextRoute.name === "search") {
      state.visible = PAGE_SIZE;
    }

    if (nextKey !== previousKey) {
      window.scrollTo({ top: 0, behavior: "auto" });
      render({ focus: nextRoute.name !== "home" });
    } else {
      render({ focus: false });
    }
  }

  function bindStaticEvents() {
    searchInput.addEventListener("input", () => {
      state.query = searchInput.value;
      updateSearchChrome();
      const hasQuery = state.query.trim().length > 0;
      if (hasQuery) {
        if (state.route.name !== "search") {
          history.pushState(null, "", `${window.location.pathname}${window.location.search}#search`);
        }
        state.route = { name: "search" };
        state.visible = PAGE_SIZE;
        render({ focus: false });
      } else if (state.route.name === "search") {
        history.replaceState(null, "", window.location.pathname + window.location.search);
        state.route = { name: "home" };
        state.activeCategory = null;
        render({ focus: false });
      }
    });

    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      state.query = searchInput.value;
      if (state.query.trim()) {
        showSearch(state.query);
      } else {
        clearSearch();
      }
    });

    searchClear.addEventListener("click", () => {
      clearSearch();
      searchInput.focus();
    });

    document.querySelectorAll("[data-search]").forEach((button) => {
      button.addEventListener("click", () => {
        showSearch(button.dataset.search || "");
        searchInput.focus();
        searchInput.setSelectionRange(searchInput.value.length, searchInput.value.length);
      });
    });

    window.addEventListener("hashchange", onHashChange);

    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const isTyping =
        target instanceof HTMLElement &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);

      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchInput.focus();
        searchInput.select();
        return;
      }

      if (event.key === "Escape") {
        if (target === searchInput && state.query) {
          event.preventDefault();
          clearSearch();
          searchInput.focus();
          return;
        }
        if (state.route.name === "detail") {
          event.preventDefault();
          window.location.hash = `#${state.route.category}`;
          return;
        }
        if (state.route.name === "category") {
          event.preventDefault();
          window.location.hash = "#";
          return;
        }
        if (state.route.name === "search" && !state.query) {
          event.preventDefault();
          if (state.activeCategory) {
            window.location.hash = `#${state.activeCategory}`;
          } else {
            window.location.hash = "#";
          }
        }
      }
    });

    viewRoot.addEventListener("change", (event) => {
      const select = event.target.closest("[data-filter]");
      if (select) {
        state.filters[select.dataset.filter] = select.value;
        state.visible = PAGE_SIZE;
        render({ focus: false });
        document.getElementById(`filter-${select.dataset.filter}`)?.focus();
        return;
      }
      if (event.target.id === "sort-select") {
        state.sort = event.target.value;
        state.visible = PAGE_SIZE;
        render({ focus: false });
        document.getElementById("sort-select")?.focus();
      }
    });

    viewRoot.addEventListener("click", (event) => {
      const loadMore = event.target.closest("[data-load-more]");
      if (loadMore) {
        state.visible += PAGE_SIZE;
        render({ focus: false });
        const next = viewRoot.querySelector("[data-load-more]");
        if (next) next.focus();
        else viewRoot.querySelector("#results-count")?.focus();
        return;
      }

      const reset = event.target.closest("[data-reset-filters]");
      if (reset) {
        state.filters = {};
        state.visible = PAGE_SIZE;
        render({ focus: false });
        document.querySelector(".filter-panel summary")?.focus();
        return;
      }

      const clear = event.target.closest("[data-clear-search]");
      if (clear) {
        clearSearch();
        searchInput.focus();
        return;
      }

      const search = event.target.closest("[data-search]");
      if (search) {
        showSearch(search.dataset.search || "");
        searchInput.focus();
        return;
      }

      const retry = event.target.closest("[data-retry]");
      if (retry) {
        loadData();
      }
    });

    document.querySelector(".skip-link")?.addEventListener("click", (event) => {
      event.preventDefault();
      const main = document.getElementById("main");
      if (main) {
        main.focus();
        main.scrollIntoView();
      }
    });

    document.querySelectorAll('a[href="#top"]').forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        window.scrollTo({ top: 0, behavior: "smooth" });
        document.getElementById("main")?.focus({ preventScroll: true });
      });
    });

    const initial = parseRoute();
    state.route = initial;
    if (initial.name === "category") {
      resetCategoryState(initial.category);
      state.activeCategory = initial.category;
    }
  }

  function start() {
    bindStaticEvents();
    loadData();
  }

  start();
})();
