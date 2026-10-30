(() => {
  "use strict";

  // Shared controller for the existing Nythara dialog and its homepage instance.
  const dialog = document.getElementById("lightbox");
  const image = document.getElementById("lightbox-image");
  const caption = document.getElementById("lightbox-caption");
  const close = document.getElementById("lightbox-close");
  if (!dialog || !image || !caption || !close || typeof dialog.showModal !== "function") return;

  const root = document.documentElement;
  const body = document.body;
  let opener = null;
  let saved = null;

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-lightbox]");
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || dialog.open) return;
    event.preventDefault();
    opener = link;
    const preview = link.querySelector("img");
    image.src = link.getAttribute("href");
    image.alt = preview?.alt || "";
    image.width = Number(preview?.getAttribute("width")) || 1600;
    image.height = Number(preview?.getAttribute("height")) || 900;
    caption.textContent = link.getAttribute("data-caption") || image.alt;

    saved = {
      x: window.scrollX, y: window.scrollY,
      rootOverflow: root.style.overflow, gutter: root.style.scrollbarGutter,
      bodyOverflow: body.style.overflow, padding: body.style.paddingRight,
    };
    const gap = window.innerWidth - root.clientWidth;
    if (gap && CSS.supports("scrollbar-gutter: stable")) root.style.scrollbarGutter = "stable";
    else if (gap) body.style.paddingRight = `${parseFloat(getComputedStyle(body).paddingRight) + gap}px`;
    root.style.overflow = "hidden";
    body.style.overflow = "hidden";
    dialog.showModal();
    close.focus({preventScroll: true});
  });

  close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  // Native dialog supplies Escape, inert background content and focus containment.
  dialog.addEventListener("close", () => {
    if (saved) {
      root.style.overflow = saved.rootOverflow;
      root.style.scrollbarGutter = saved.gutter;
      body.style.overflow = saved.bodyOverflow;
      body.style.paddingRight = saved.padding;
      const behavior = root.style.scrollBehavior;
      root.style.scrollBehavior = "auto";
      window.scrollTo(saved.x, saved.y);
      root.style.scrollBehavior = behavior;
      saved = null;
    }
    opener?.focus({preventScroll: true});
    opener = null;
  });
})();
