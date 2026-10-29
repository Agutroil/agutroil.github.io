(() => {
  "use strict";

  document.querySelector(".skip-link")?.addEventListener("click", () => {
    document.getElementById("main")?.focus({ preventScroll: true });
  });

  const menuToggle = document.getElementById("menu-toggle");
  const navLinks = document.getElementById("nav-links");

  if (menuToggle && navLinks) {
    const setMenu = (open) => {
      menuToggle.setAttribute("aria-expanded", String(open));
      menuToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
      navLinks.classList.toggle("is-open", open);
    };

    menuToggle.addEventListener("click", () => {
      setMenu(menuToggle.getAttribute("aria-expanded") !== "true");
    });

    navLinks.addEventListener("click", (event) => {
      if (event.target.closest("a")) {
        setMenu(false);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menuToggle.getAttribute("aria-expanded") === "true") {
        setMenu(false);
        menuToggle.focus();
      }
    });

    document.addEventListener("focusin", (event) => {
      if (!navLinks.contains(event.target) && event.target !== menuToggle) {
        setMenu(false);
      }
    });

    document.addEventListener("click", (event) => {
      if (menuToggle.getAttribute("aria-expanded") !== "true") return;
      if (!navLinks.contains(event.target) && !menuToggle.contains(event.target)) {
        setMenu(false);
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 980) {
        setMenu(false);
      }
    });
  }

  const sections = Array.from(document.querySelectorAll("main section[id]"));
  const navItems = Array.from(document.querySelectorAll("[data-nav]"));

  if ("IntersectionObserver" in window && navItems.length) {
    const navObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const id = entry.target.id;
        navItems.forEach((link) => {
          if (link.getAttribute("href") === `#${id}`) {
            link.setAttribute("aria-current", "location");
          } else {
            link.removeAttribute("aria-current");
          }
        });
      });
    }, { rootMargin: "-35% 0px -55% 0px" });

    sections.forEach((section) => navObserver.observe(section));
  }

  const dialog = document.getElementById("lightbox");
  const dialogImage = document.getElementById("lightbox-image");
  const dialogCaption = document.getElementById("lightbox-caption");
  const dialogClose = document.getElementById("lightbox-close");
  let lightboxOpener = null;

  if (dialog && dialogImage && dialogCaption && typeof dialog.showModal === "function") {
    document.querySelectorAll("[data-lightbox]").forEach((link) => {
      link.addEventListener("click", (event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        lightboxOpener = link;
        dialogImage.src = link.getAttribute("href");
        const preview = link.querySelector("img");
        dialogImage.alt = preview?.alt || "";
        dialogImage.width = Number(preview?.getAttribute("width")) || 1600;
        dialogImage.height = Number(preview?.getAttribute("height")) || 900;
        dialogCaption.textContent = link.getAttribute("data-caption") || "";
        dialog.showModal();
        dialogClose?.focus();
      });
    });

    dialogClose?.addEventListener("click", () => dialog.close());

    dialog.addEventListener("close", () => {
      lightboxOpener?.focus({ preventScroll: true });
      lightboxOpener = null;
    });

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  }
})();
