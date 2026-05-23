/* ═══════════════════════════════════════════════════════
   College Club Event Management System – main.js
═══════════════════════════════════════════════════════ */

// ── Sidebar toggle ─────────────────────────────────────
function toggleSidebar() {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('open');
}

// ── Delete confirmation modal ──────────────────────────
function confirmDelete(actionUrl, itemName) {
  const modal    = document.getElementById('deleteModal');
  const nameEl   = document.getElementById('deleteItemName');
  const formEl   = document.getElementById('deleteForm');
  if (!modal || !nameEl || !formEl) return;
  nameEl.textContent = itemName;
  formEl.action = actionUrl;
  const bsModal = new bootstrap.Modal(modal);
  bsModal.show();
}

// ── Loading spinner on form submit ─────────────────────
document.addEventListener('DOMContentLoaded', function () {

  // Auto-dismiss alerts after 4 seconds
  document.querySelectorAll('.alert.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  // Spinner on submit buttons
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      const btn     = form.querySelector('#submitBtn, #loginBtn, #collegeBtn, #pwBtn');
      const spinner = form.querySelector('[id$="Spinner"]');
      const text    = form.querySelector('.btn-text');
      if (btn && spinner) {
        btn.disabled = true;
        spinner.classList.remove('d-none');
        if (text) text.classList.add('d-none');
      }
    });
  });

  // Toast helper (can be called from anywhere)
  window.showToast = function (message, type) {
    type = type || 'success';
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const id = 'toast_' + Date.now();
    const icons = {
      success: 'check-circle-fill',
      danger:  'x-circle-fill',
      warning: 'exclamation-triangle-fill',
      info:    'info-circle-fill'
    };
    const html = `
      <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
        <div class="d-flex">
          <div class="toast-body">
            <i class="bi bi-${icons[type] || 'info-circle-fill'} me-2"></i>${message}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      </div>`;
    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(id);
    const toast   = new bootstrap.Toast(toastEl, { delay: 3500 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', function () { toastEl.remove(); });
  };
});
