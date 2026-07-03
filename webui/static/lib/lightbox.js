// Global image lightbox.
//
// ``init()`` wires up close handlers and a body-level delegated click
// for any element with ``.image-preview-trigger`` (the same convention
// the legacy app.js used). Plain page images are also previewable so paper
// figures, markdown images, demo posters, and task assets share one behavior.

let inited = false;
let dom = null;

export function init() {
  if (inited) return;
  inited = true;
  dom = {
    root: document.getElementById("image-lightbox"),
    backdrop: document.getElementById("lightbox-backdrop"),
    close: document.getElementById("lightbox-close"),
    image: document.getElementById("lightbox-image"),
    caption: document.getElementById("lightbox-caption"),
  };
  if (!dom.root) return;
  dom.backdrop?.addEventListener("click", hide);
  dom.close?.addEventListener("click", hide);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !dom.root.classList.contains("hidden")) {
      event.preventDefault();
      event.stopImmediatePropagation();
      hide();
    }
  });
  document.body.addEventListener("click", (event) => {
    const trigger = event.target.closest(".image-preview-trigger");
    const plainImage = trigger ? null : event.target.closest("img");
    if (!trigger && !plainImage) return;
    if (plainImage && shouldIgnorePlainImage(plainImage)) return;
    const innerImg = trigger?.querySelector("img");
    const src = trigger?.dataset?.previewSrc
      || trigger?.getAttribute("src")
      || trigger?.getAttribute("href")
      || innerImg?.getAttribute("src");
    const fallbackSrc = plainImage?.currentSrc || plainImage?.getAttribute("src");
    if (!src && !fallbackSrc) return;
    event.preventDefault();
    const caption = trigger?.dataset?.previewCaption || trigger?.alt || innerImg?.alt || plainImage?.alt || "";
    show(src || fallbackSrc, caption);
  });
}

function shouldIgnorePlainImage(img) {
  if (!img || img.id === "lightbox-image" || img.closest("#image-lightbox")) return true;
  if (img.closest("video")) return true;
  return false;
}

export function show(src, caption = "") {
  if (!dom?.root) return;
  dom.image.src = src;
  dom.image.alt = caption || "";
  dom.caption.textContent = caption || "";
  dom.root.classList.remove("hidden");
  dom.root.setAttribute("aria-hidden", "false");
}

export function hide() {
  if (!dom?.root) return;
  dom.root.classList.add("hidden");
  dom.root.setAttribute("aria-hidden", "true");
  dom.image.src = "";
  dom.image.alt = "";
  dom.caption.textContent = "";
}
