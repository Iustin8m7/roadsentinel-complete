// Applies the saved theme before first paint (external file: strict CSP, no inline script).
try {
  if (localStorage.getItem("rs-calm") === "on")
    document.documentElement.setAttribute("data-calm", "on");
  var t = localStorage.getItem("rs-theme");
  if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
} catch (e) {
  /* storage blocked: follow the system */
}
