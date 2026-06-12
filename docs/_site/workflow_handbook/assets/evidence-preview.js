(function () {
  const dataEl = document.getElementById("evidence-preview-data");
  const popover = document.querySelector(".evidence-popover");
  if (!dataEl || !popover) return;

  let previews = {};
  let activeAnchor = null;
  let hideTimer = 0;
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

  function previewForAnchor(anchor) {
    const ref = anchor.getAttribute("data-ref");
    if (ref) return referencePreviewFor(ref);
    const marker = anchor.getAttribute("data-marker");
    if (marker) return previewFor(marker);
    const previewId = anchor.getAttribute("data-preview-id");
    if (!previewId) return null;
    return referencePreviewFor(previewId) || previewFor(previewId);
  }

  function place(anchor) {
    const rect = anchor.getBoundingClientRect();
    const gap = 10;
    const left = Math.min(
      rect.left,
      window.innerWidth - popover.offsetWidth - 16
    );
    const below = rect.bottom + gap;
    const above = rect.top - popover.offsetHeight - gap;
    const top =
      below + popover.offsetHeight <= window.innerHeight - 16
        ? below
        : Math.max(16, above);
    popover.style.left = Math.max(16, left) + "px";
    popover.style.top = Math.max(16, top) + "px";
  }

  function show(event) {
    const anchor = event.currentTarget;
    const marker =
      anchor.getAttribute("data-ref") ||
      anchor.getAttribute("data-marker") ||
      anchor.getAttribute("data-preview-id");
    const preview = previewForAnchor(anchor);
    if (!preview) return;
    activeAnchor = anchor;
    clearTimeout(hideTimer);
    popover.innerHTML = "";
    const title = document.createElement("strong");
    title.textContent = preview.title || marker;
    const excerpt = document.createElement("p");
    excerpt.textContent = preview.excerpt || preview.body || "No preview recorded.";
    const meta = document.createElement("p");
    meta.className = "muted";
    meta.textContent = [
      preview.path,
      preview.support_relation,
      preview.kind,
      preview.truth_status
    ]
      .filter(Boolean)
      .join(" | ");
    popover.append(title, excerpt, meta);
    popover.style.display = "block";
    place(anchor);
  }

  function hide() {
    activeAnchor = null;
    popover.style.display = "none";
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, 140);
  }

  document.querySelectorAll("[data-preview-id]").forEach((el) => {
    el.addEventListener("mouseenter", show);
    el.addEventListener("focus", show);
    el.addEventListener("mouseleave", scheduleHide);
    el.addEventListener("blur", scheduleHide);
  });

  popover.addEventListener("mouseenter", () => clearTimeout(hideTimer));
  popover.addEventListener("mouseleave", scheduleHide);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hide();
  });
  window.addEventListener("resize", () => {
    if (activeAnchor && popover.style.display === "block") place(activeAnchor);
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

(function () {
  document.querySelectorAll("[data-terminal]").forEach((terminal) => {
    const dataEl = terminal.querySelector("[data-terminal-data]");
    const current = terminal.querySelector("[data-terminal-current]");
    const output = terminal.querySelector("[data-terminal-output]");
    const copy = terminal.querySelector("[data-terminal-copy]");
    const buttons = Array.from(
      terminal.querySelectorAll("[data-terminal-index]")
    );
    if (!dataEl || !current || !output || !buttons.length) return;

    let commands = [];
    try {
      commands = JSON.parse(dataEl.textContent || "[]");
    } catch (error) {
      return;
    }

    function commandAt(index) {
      return commands[index] || commands[0] || {};
    }

    function select(index) {
      const command = commandAt(index);
      current.textContent = command.command || "";
      output.textContent = command.output || "";
      buttons.forEach((button) => {
        const isActive = Number(button.dataset.terminalIndex) === index;
        button.classList.toggle("active", isActive);
      });
      if (copy) copy.textContent = "Copy command";
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        select(Number(button.dataset.terminalIndex || 0));
      });
    });

    if (copy) {
      copy.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(current.textContent || "");
          copy.textContent = "Copied";
        } catch (error) {
          copy.textContent = "Select command";
        }
        window.setTimeout(() => {
          copy.textContent = "Copy command";
        }, 1600);
      });
    }

    select(0);
  });
})();
