/* Oceanica Terra · menú superior (diseño B): se despliega al pasar el mouse en computadora; botón y acordeón en celular y tableta. */
(() => {
  const head = document.querySelector("header.top");
  const burger = head.querySelector(".gn-burger");
  const wide = matchMedia("(hover: hover) and (min-width: 1100px)");
  const setOpen = (on) => {
    head.classList.toggle("open", on);
    burger.setAttribute("aria-expanded", on);
    burger.setAttribute("aria-label", on ? "Cerrar el menú" : "Abrir el menú");
    document.body.classList.toggle("gn-lock", on);
  };
  burger.addEventListener("click", () => setOpen(!head.classList.contains("open")));
  head.querySelectorAll(".gn-exp").forEach(b => b.addEventListener("click", () => {
    const li = b.closest(".gn-item"); const on = !li.classList.contains("open");
    li.classList.toggle("open", on); b.setAttribute("aria-expanded", on);
  }));
  head.querySelectorAll("nav a").forEach(a => a.addEventListener("click", () => {
    const tab = a.dataset.tab && document.getElementById(a.dataset.tab);
    if (tab) tab.click();
    if (wide.matches) { hushed = a.closest(".gn-item"); head.classList.add("gn-hush"); a.blur(); }
    else setOpen(false);
  }));
  let hushed = null;
  head.addEventListener("mouseleave", () => { head.classList.remove("gn-hush"); hushed = null; });
  head.querySelectorAll(".gn-item").forEach(li => li.addEventListener("mouseenter", () => {
    if (hushed && li !== hushed) { head.classList.remove("gn-hush"); hushed = null; }
  }));
  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    if (head.classList.contains("open")) setOpen(false);
    if (head.contains(document.activeElement)) document.activeElement.blur();
  });
  wide.addEventListener("change", () => setOpen(false));
})();
