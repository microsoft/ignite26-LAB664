const contents = document.querySelector(".contents");
const wide = window.matchMedia("(min-width: 64rem)");

function adaptContents() {
  contents.open = wide.matches;
}

adaptContents();
wide.addEventListener("change", adaptContents);
contents.addEventListener("click", (event) => {
  if (event.target.closest("a") && !wide.matches) contents.open = false;
});

function followSlideLink() {
  const match = /^#\/(\d+)$/.exec(window.location.hash);
  if (!match) return;
  const target = document.getElementById(`slide-${match[1]}`);
  if (!target) return;
  window.history.replaceState(null, "", `#${target.id}`);
  target.scrollIntoView();
}

followSlideLink();
window.addEventListener("hashchange", followSlideLink);

const lightbox = document.querySelector(".slide-lightbox");
const lightboxImage = lightbox.querySelector(".lightbox-image");
const lightboxViewport = lightbox.querySelector(".lightbox-viewport");
const lightboxTitle = lightbox.querySelector("#lightbox-title");
const lightboxZoom = lightbox.querySelector(".lightbox-zoom");
const lightboxStatus = lightbox.querySelector(".lightbox-status");
let returnLink;
let articlePosition = 0;

function resetZoom() {
  lightbox.classList.remove("is-zoomed");
  lightboxZoom.setAttribute("aria-pressed", "false");
  lightboxZoom.textContent = "Zoom in";
  lightboxViewport.scrollTo(0, 0);
}

document.addEventListener("click", (event) => {
  const link = event.target.closest("a.slide-enlarge");
  if (!link || event.defaultPrevented || event.button !== 0 ||
      event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ||
      typeof lightbox.showModal !== "function") return;
  event.preventDefault();
  returnLink = link;
  articlePosition = window.scrollY;
  const number = link.dataset.slide;
  const source = link.closest("figure").querySelector("img");
  lightboxTitle.textContent = `Slide ${number}`;
  lightboxImage.alt = source.alt;
  lightboxStatus.hidden = true;
  lightboxImage.src = link.href;
  lightbox.querySelector(".lightbox-original").href = `presentation.html#/${number}`;
  resetZoom();
  lightbox.showModal();
  document.documentElement.classList.add("lightbox-open");
});

lightboxZoom.addEventListener("click", () => {
  const zoomed = lightbox.classList.toggle("is-zoomed");
  lightboxZoom.setAttribute("aria-pressed", String(zoomed));
  lightboxZoom.textContent = zoomed ? "Fit to screen" : "Zoom in";
  lightboxViewport.scrollTo(0, 0);
});

lightboxImage.addEventListener("error", () => {
  lightboxStatus.textContent = "The slide image could not load. Return to the article or open the animated slide.";
  lightboxStatus.hidden = false;
});

lightbox.addEventListener("click", (event) => {
  if (event.target !== lightbox) return;
  const bounds = lightbox.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right ||
      event.clientY < bounds.top || event.clientY > bounds.bottom) lightbox.close();
});

lightbox.addEventListener("close", () => {
  document.documentElement.classList.remove("lightbox-open");
  returnLink?.focus({ preventScroll: true });
  window.scrollTo({ top: articlePosition, behavior: "instant" });
  resetZoom();
});
