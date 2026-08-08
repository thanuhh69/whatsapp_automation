// OptOuts Module
const OptOuts = {
  init() {
    this.bindEvents();
    this.loadOptOuts();
  },

  bindEvents() {
    const addBtn = document.getElementById("add-optout-btn");
    if (addBtn) addBtn.addEventListener("click", () => this.addOptOut());
  },

  async loadOptOuts() {
    try {
      const data = await App.apiRequest("/api/opt-outs");
      this.renderTable(data);
    } catch (e) {
      console.error(e);
    }
  },

  renderTable(items) {
    const tbody = document.getElementById("optouts-table-body");
    if (!tbody) return;

    if (!items || items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No opt-out records present.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map(o => `
      <tr>
        <td><code>${o.phone}</code></td>
        <td><span class="badge ${o.source === 'auto_keyword' ? 'badge-warning' : 'badge-secondary'}">${o.source}</span></td>
        <td>${o.reason || "-"}</td>
        <td>
          <button class="btn btn-sm btn-danger" onclick="OptOuts.deleteOptOut(${o.id})">
            <i class="ri-delete-bin-line"></i> Remove
          </button>
        </td>
      </tr>
    `).join("");
  },

  async addOptOut() {
    const phone = document.getElementById("optout-phone-input").value.trim();
    const reason = document.getElementById("optout-reason-input").value.trim();

    if (!phone) {
      App.showToast("Please provide a mobile number.", "error");
      return;
    }

    try {
      await App.apiRequest("/api/opt-outs", "POST", { phone, reason, source: "manual" });
      App.showToast(`Number ${phone} added to Opt-Out registry.`, "success");

      document.getElementById("optout-phone-input").value = "";
      document.getElementById("optout-reason-input").value = "";

      this.loadOptOuts();
      Dashboard.loadStats();
    } catch (e) {
      console.error(e);
    }
  },

  async deleteOptOut(id) {
    try {
      await App.apiRequest(`/api/opt-outs/${id}`, "DELETE");
      App.showToast("Opt-out record removed.", "info");
      this.loadOptOuts();
      Dashboard.loadStats();
    } catch (e) {
      console.error(e);
    }
  }
};
