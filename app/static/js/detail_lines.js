function addDetailLine() {
  const tbody = document.getElementById("detail-lines-body");
  const template = document.getElementById("detail-line-template");
  const clone = template.content.cloneNode(true);
  tbody.appendChild(clone);
}

function removeDetailLine(btn) {
  const rows = document.querySelectorAll("#detail-lines-body tr");
  if (rows.length <= 1) {
    return;
  }
  btn.closest("tr").remove();
}

document.addEventListener("DOMContentLoaded", () => {
  const addBtn = document.getElementById("btn-add-line");
  if (addBtn) {
    addBtn.addEventListener("click", addDetailLine);
  }
  document.getElementById("detail-lines-body")?.addEventListener("click", (e) => {
    if (e.target.classList.contains("btn-remove-line")) {
      removeDetailLine(e.target);
    }
  });
});
