// Recipients Module
const Recipients = {
  currentPage: 1,
  pageSize: 20,

  init() {
    this.bindEvents();
    this.loadRecipients();
  },

  bindEvents() {
    const searchInput = document.getElementById("recipient-search-input");
    if (searchInput) {
      let timer;
      searchInput.addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          this.currentPage = 1;
          this.loadRecipients();
        }, 300);
      });
    }

    const filterSelect = document.getElementById("recipient-status-filter");
    if (filterSelect) {
      filterSelect.addEventListener("change", () => {
        this.currentPage = 1;
        this.loadRecipients();
      });
    }

    const syncBtn = document.getElementById("recipients-sync-btn");
    if (syncBtn) {
      syncBtn.addEventListener("click", () => this.triggerSync(false));
    }

    const replaceSyncBtn = document.getElementById("recipients-replace-sync-btn");
    if (replaceSyncBtn) {
      replaceSyncBtn.addEventListener("click", () => this.triggerSync(true));
    }

    const prevBtn = document.getElementById("recipients-prev-btn");
    const nextBtn = document.getElementById("recipients-next-btn");
    if (prevBtn) prevBtn.addEventListener("click", () => { if (this.currentPage > 1) { this.currentPage--; this.loadRecipients(); } });
    if (nextBtn) nextBtn.addEventListener("click", () => { this.currentPage++; this.loadRecipients(); });
  },

  async loadRecipients() {
    const search = document.getElementById("recipient-search-input").value;
    const status = document.getElementById("recipient-status-filter").value;

    let url = `/api/recipients?page=${this.currentPage}&page_size=${this.pageSize}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;

    try {
      const data = await App.apiRequest(url);
      this.renderTable(data.items);
      this.updatePagination(data.total, data.page, data.page_size);
    } catch (e) {
      console.error(e);
    }
  },

  renderTable(items) {
    const tbody = document.getElementById("recipients-table-body");
    if (!tbody) return;

    if (!items || items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No recipients found. Click "Sync Google Sheet" to populate recipients from your configured sheet.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map(r => `
      <tr>
        <td>#${r.id}</td>
        <td><strong>${r.name}</strong></td>
        <td><code>${r.phone}</code></td>
        <td class="text-muted">${r.phone_raw}</td>
        <td>${r.email || "-"}</td>
        <td><span class="badge ${r.consent ? "badge-success" : "badge-danger"}">${r.consent ? "YES" : "NO"}</span></td>
        <td>
          ${r.is_opted_out
            ? '<span class="badge badge-danger">OPTED OUT</span>'
            : (r.status === 'DEACTIVATED'
                ? '<span class="badge badge-secondary">DEACTIVATED</span>'
                : '<span class="badge badge-success">ACTIVE</span>')}
        </td>
        <td>
          ${r.status === 'DEACTIVATED'
            ? `<button class="btn btn-sm btn-outline" onclick="Recipients.toggleActivate(${r.id}, true)"><i class="ri-check-line"></i> Activate</button>`
            : `<button class="btn btn-sm btn-outline" onclick="Recipients.toggleActivate(${r.id}, false)"><i class="ri-close-line"></i> Deactivate</button>`}
        </td>
      </tr>
    `).join("");
  },

  updatePagination(total, page, pageSize) {
    const info = document.getElementById("recipients-pagination-info");
    if (info) {
      const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
      const end = Math.min(total, page * pageSize);
      info.textContent = `Showing ${start}-${end} of ${total} registrants`;
    }
  },

  async toggleActivate(id, activate) {
    const endpoint = `/api/recipients/${id}/${activate ? 'activate' : 'deactivate'}`;
    try {
      const res = await App.apiRequest(endpoint, "PUT");
      App.showToast(res.message, "info");
      this.loadRecipients();
      Dashboard.loadStats();
    } catch (e) {
      console.error(e);
    }
  },

  async triggerSync(replaceAll = false) {
    if (replaceAll && !confirm("Replace local recipient list with current Google Sheet data? Local recipients not present in sheet will be deactivated.")) {
      return;
    }
    App.showToast("Starting Google Sheets sync...", "info");
    try {
      const url = replaceAll ? "/api/recipients/replace-from-sheet" : "/api/recipients/sync";
      const report = await App.apiRequest(url, "POST");
      App.showToast(
        `Sync Result -> Added: ${report.added}, Updated: ${report.updated}, Deactivated: ${report.deactivated || 0}, Ignored: ${report.ignored}, Invalid: ${report.invalid}, Duplicates: ${report.duplicates || 0}`,
        "success"
      );
      this.loadRecipients();
      Dashboard.loadStats();
    } catch (e) {
      console.error(e);
    }
  }
};
