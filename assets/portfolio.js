(() => {
  "use strict";
  const toggle = document.getElementById("menu-toggle");
  const nav = document.getElementById("nav-links");
  const mobile = window.matchMedia("(max-width: 640px)");
  if (!toggle || !nav) return;

  const setMenu = (open) => {
    nav.hidden = mobile.matches && !open;
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Schließen" : "Menü";
  };
  const sync = () => {
    // Navigation stays fully available if JavaScript fails or is disabled.
    if (!mobile.matches && document.activeElement === toggle) nav.querySelector("a")?.focus();
    if (mobile.matches && nav.contains(document.activeElement)) toggle.focus();
    toggle.hidden = !mobile.matches;
    setMenu(false);
  };
  sync();
  mobile.addEventListener("change", sync);
  toggle.addEventListener("click", () => setMenu(toggle.getAttribute("aria-expanded") !== "true"));
  nav.addEventListener("click", (event) => {
    const link = event.target.closest("a");
    if (!link || !mobile.matches) return;
    const section = link.hash && document.getElementById(link.hash.slice(1));
    setMenu(false);
    if (section) section.focus({preventScroll: true});
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mobile.matches && !nav.hidden) {
      setMenu(false);
      toggle.focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".nav")) setMenu(false);
  });
  document.addEventListener("focusin", (event) => {
    if (!event.target.closest(".nav")) setMenu(false);
  });
})();
