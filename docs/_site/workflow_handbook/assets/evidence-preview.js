(function () {
  const dataEl = document.getElementById("evidence-preview-data");
  const popover = document.querySelector(".evidence-popover");
  if (!dataEl || !popover) return;

  let previews = {};
  try {
    previews = JSON.parse(dataEl.textContent || "{}");
  } catch (error) {
    return;
  }

  function previewFor(marker) {
    const item = (previews.markers || {})[marker];
    if (item && item.previews && item.previews.length) return item.previews[0];
    return (previews.evidence || {})[marker] || null;
  }

  function show(event) {
    const marker = event.currentTarget.getAttribute("data-marker");
    const ref = event.currentTarget.getAttribute("data-ref");
    const preview = ref ? referencePreviewFor(ref) : previewFor(marker);
    if (!preview) return;
    popover.innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = preview.title || marker;
    const excerpt = document.createElement("p");
    excerpt.textContent = preview.excerpt || "No excerpt recorded.";
    const meta = document.createElement("p");
    meta.className = "muted";
    meta.textContent = [preview.path, preview.support_relation]
      .filter(Boolean)
      .join(" | ");
    popover.append(title, excerpt, meta);
    popover.style.display = "block";
    const rect = event.currentTarget.getBoundingClientRect();
    const left = Math.min(rect.left, window.innerWidth - popover.offsetWidth - 16);
    const top = Math.min(
      rect.bottom + 8,
      window.innerHeight - popover.offsetHeight - 16
    );
    popover.style.left = Math.max(16, left) + "px";
    popover.style.top = Math.max(16, top) + "px";
  }

  function hide() {
    popover.style.display = "none";
  }

  document.querySelectorAll(".evidence-marker").forEach((el) => {
    el.addEventListener("mouseenter", show);
    el.addEventListener("focus", show);
    el.addEventListener("mouseleave", hide);
    el.addEventListener("blur", hide);
  });
  document.querySelectorAll(".reference-marker").forEach((el) => {
    el.addEventListener("mouseenter", show);
    el.addEventListener("focus", show);
    el.addEventListener("mouseleave", hide);
    el.addEventListener("blur", hide);
  });

  function referencePreviewFor(ref) {
    const entry = (previews.entries || {})[ref];
    if (!entry) return null;
    const card = entry.preview || {};
    const paths = (entry.source_paths || []).map((item) => item.path).filter(Boolean);
    return {
      title: card.title || entry.title || ref,
      excerpt: card.body || entry.summary || "No preview recorded.",
      path: paths.join(", "),
      support_relation: [entry.kind, entry.truth_status, entry.owner]
        .filter(Boolean)
        .join(" | "),
    };
  }
})();
