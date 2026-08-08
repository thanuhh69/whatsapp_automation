// Campaigns Module
const Campaigns = {
  activeCampaignId: null,
  pollTimer: null,
  selectedCampaignIds: new Set(),

  init() {
    this.bindEvents();
    this.loadCampaigns();
  },

  bindEvents() {
    const openModalBtn = document.getElementById("open-create-campaign-modal");
    const closeModalBtn = document.getElementById("close-campaign-modal");
    const cancelModalBtn = document.getElementById("cancel-campaign-modal");
    const modal = document.getElementById("campaign-modal");

    if (openModalBtn) {
      openModalBtn.addEventListener("click", () => {
        modal.classList.add("active");
        this.loadRecipientPicker();
      });
    }
    if (closeModalBtn) closeModalBtn.addEventListener("click", () => modal.classList.remove("active"));
    if (cancelModalBtn) cancelModalBtn.addEventListener("click", () => modal.classList.remove("active"));

    const modalTplSelect = document.getElementById("modal-campaign-template-select");
    if (modalTplSelect) {
      modalTplSelect.addEventListener("change", (e) => {
        const id = e.target.value;
        const tpl = Templates.templates.find(t => t.id === id);
        if (tpl) {
          document.getElementById("modal-campaign-template-text").value = tpl.content;
          document.getElementById("modal-campaign-name").value = `${tpl.name} Campaign`;
        }
      });
    }

    const modeRadios = document.querySelectorAll('input[name="recipient-target-mode"]');
    const picker = document.getElementById("modal-recipient-picker");
    modeRadios.forEach(r => {
      r.addEventListener("change", (e) => {
        if (picker) picker.style.display = e.target.value === "select" ? "block" : "none";
      });
    });

    const confirmCreateBtn = document.getElementById("confirm-create-campaign-btn");
    if (confirmCreateBtn) {
      confirmCreateBtn.addEventListener("click", () => this.createCampaign());
    }

    const startBtn = document.getElementById("cd-start-btn");
    const stopBtn = document.getElementById("cd-stop-btn");
    const retryBtn = document.getElementById("cd-retry-failed-btn");
    const deleteBtn = document.getElementById("cd-delete-btn");

    if (startBtn) startBtn.addEventListener("click", () => this.startCampaign());
    if (stopBtn) stopBtn.addEventListener("click", () => this.stopCampaign());
    if (retryBtn) retryBtn.addEventListener("click", () => this.retryFailed());
    if (deleteBtn) deleteBtn.addEventListener("click", () => this.deleteCurrentCampaign());

    const selectAllCb = document.getElementById("select-all-campaigns-checkbox");
    if (selectAllCb) {
      selectAllCb.addEventListener("change", (e) => {
        const checkboxes = document.querySelectorAll(".campaign-row-checkbox");
        checkboxes.forEach(cb => {
          cb.checked = e.target.checked;
          const id = parseInt(cb.value, 10);
          if (e.target.checked) this.selectedCampaignIds.add(id);
          else this.selectedCampaignIds.delete(id);
        });
        this.updateBulkDeleteUI();
      });
    }

    const bulkDeleteBtn = document.getElementById("bulk-delete-campaigns-btn");
    if (bulkDeleteBtn) {
      bulkDeleteBtn.addEventListener("click", () => this.bulkDelete());
    }
  },

  async loadRecipientPicker() {
    try {
      const data = await App.apiRequest("/api/recipients?status=eligible&page_size=100");
      const items = data.items || [];
      const countSpan = document.getElementById("modal-eligible-count");
      if (countSpan) countSpan.textContent = items.length;

      const picker = document.getElementById("modal-recipient-picker");
      if (picker) {
        if (!items.length) {
          picker.innerHTML = `<div class="text-muted">No eligible recipients found. Please sync Google Sheet first.</div>`;
        } else {
          picker.innerHTML = items.map(r => `
            <div style="margin-bottom: 0.25rem;">
              <label style="font-size: 0.825rem; font-weight: normal; cursor: pointer;">
                <input type="checkbox" class="recipient-picker-cb" value="${r.id}" checked>
                ${r.name} (<code>${r.phone}</code>)
              </label>
            </div>
          `).join("");
        }
      }
    } catch (e) {
      console.error(e);
    }
  },

  async loadCampaigns() {
    try {
      const campaigns = await App.apiRequest("/api/campaigns");
      this.renderTable(campaigns);
    } catch (e) {
      console.error(e);
    }
  },

  renderTable(campaigns) {
    const tbody = document.getElementById("campaigns-table-body");
    if (!tbody) return;

    if (!campaigns || campaigns.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No campaigns created yet. Click "Create New Campaign" to start.</td></tr>`;
      return;
    }

    tbody.innerHTML = campaigns.map(c => `
      <tr>
        <td><input type="checkbox" class="campaign-row-checkbox" value="${c.id}" ${this.selectedCampaignIds.has(c.id) ? 'checked' : ''} onchange="Campaigns.toggleSelect(${c.id}, this.checked)"></td>
        <td>#${c.id}</td>
        <td><strong>${c.name}</strong></td>
        <td><span class="badge ${this.getStatusBadgeClass(c.status)}">${c.status}</span></td>
        <td><span class="badge ${c.is_test_mode ? "badge-warning" : "badge-secondary"}">${c.is_test_mode ? "TEST" : "REAL"}</span></td>
        <td>${c.total_recipients}</td>
        <td>${c.sent_count} / <span style="color: var(--accent-red);">${c.failed_count}</span></td>
        <td class="text-muted">${App.formatDate(c.created_at)}</td>
        <td>
          <div class="flex-gap">
            <button class="btn btn-sm btn-outline" onclick="Campaigns.viewDetail(${c.id})">
              <i class="ri-eye-line"></i> View
            </button>
            <button class="btn btn-sm btn-danger" onclick="Campaigns.deleteCampaign(${c.id})">
              <i class="ri-delete-bin-line"></i> Delete
            </button>
          </div>
        </td>
      </tr>
    `).join("");
  },

  toggleSelect(id, checked) {
    if (checked) this.selectedCampaignIds.add(id);
    else this.selectedCampaignIds.delete(id);
    this.updateBulkDeleteUI();
  },

  updateBulkDeleteUI() {
    const bulkBtn = document.getElementById("bulk-delete-campaigns-btn");
    const countSpan = document.getElementById("selected-campaign-count");
    if (bulkBtn && countSpan) {
      const size = this.selectedCampaignIds.size;
      countSpan.textContent = size;
      bulkBtn.style.display = size > 0 ? "inline-flex" : "none";
    }
  },

  getStatusBadgeClass(status) {
    if (status === "COMPLETED") return "badge-success";
    if (status === "SENDING") return "badge-warning";
    if (status === "STOPPED" || status === "FAILED") return "badge-danger";
    return "badge-secondary";
  },

  async createCampaign() {
    const name = document.getElementById("modal-campaign-name").value.trim();
    const templateText = document.getElementById("modal-campaign-template-text").value.trim();
    const isTest = document.getElementById("modal-campaign-testmode").checked;
    const mode = document.querySelector('input[name="recipient-target-mode"]:checked').value;

    if (!name || !templateText) {
      App.showToast("Campaign name and message template are required.", "error");
      return;
    }

    let recipientIds = null;
    if (mode === "select") {
      const checkedBoxes = document.querySelectorAll(".recipient-picker-cb:checked");
      recipientIds = Array.from(checkedBoxes).map(cb => parseInt(cb.value, 10));
      if (!recipientIds.length) {
        App.showToast("Please select at least one recipient.", "error");
        return;
      }
    }

    try {
      const payload = {
        name: name,
        message_template: templateText,
        recipient_ids: recipientIds,
        is_test_mode: isTest
      };

      const campaign = await App.apiRequest("/api/campaigns", "POST", payload);
      App.showToast(`Campaign '${campaign.name}' created successfully!`, "success");

      document.getElementById("campaign-modal").classList.remove("active");
      this.loadCampaigns();
      this.viewDetail(campaign.id);
    } catch (e) {
      console.error(e);
    }
  },

  async viewDetail(campaignId) {
    this.activeCampaignId = campaignId;
    const detailCard = document.getElementById("campaign-detail-card");
    if (detailCard) detailCard.style.display = "block";

    this.refreshDetail();

    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = setInterval(() => {
      if (this.activeCampaignId === campaignId) {
        this.refreshDetail();
      }
    }, 2500);
  },

  async refreshDetail() {
    if (!this.activeCampaignId) return;

    try {
      const c = await App.apiRequest(`/api/campaigns/${this.activeCampaignId}`);
      document.getElementById("cd-title").textContent = `Campaign #${c.id}: ${c.name}`;
      document.getElementById("cd-status").textContent = `Status: ${c.status} | Mode: ${c.is_test_mode ? "TEST MODE (Simulation)" : "REAL WHATSAPP SEND"}`;

      const total = c.total_recipients || 1;
      const processed = c.sent_count + c.failed_count + c.skipped_count;
      const pct = Math.min(100, Math.round((processed / total) * 100));

      document.getElementById("cd-progress-bar").style.width = `${pct}%`;
      document.getElementById("cd-progress-text").textContent = `${processed} of ${c.total_recipients} Processed (${pct}%)`;
      document.getElementById("cd-sent-failed-text").textContent = `Sent: ${c.sent_count} | Failed: ${c.failed_count} | Skipped: ${c.skipped_count}`;

      // Load message details
      const msgData = await App.apiRequest(`/api/campaigns/${this.activeCampaignId}/messages?page_size=100`);
      this.renderMessagesTable(msgData.items);

      this.loadCampaigns();
    } catch (e) {
      console.error(e);
    }
  },

  renderMessagesTable(messages) {
    const tbody = document.getElementById("cd-messages-table-body");
    if (!tbody) return;

    if (!messages || messages.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No messages found for this campaign.</td></tr>`;
      return;
    }

    tbody.innerHTML = messages.map(m => `
      <tr>
        <td>${m.recipient_name || "Recipient #" + m.recipient_id}</td>
        <td><code>${m.recipient_phone || "-"}</code></td>
        <td style="max-width: 320px; word-break: break-word;">${m.rendered_message}</td>
        <td><span class="badge ${this.getStatusBadgeClass(m.status)}">${m.status}</span></td>
        <td class="text-muted">${m.error ? '<span style="color:var(--accent-red);">' + m.error + '</span>' : App.formatDate(m.sent_at, true)}</td>
      </tr>
    `).join("");
  },

  async startCampaign() {
    if (!this.activeCampaignId) return;
    if (!confirm("Are you sure you want to start executing this campaign?")) return;
    try {
      const res = await App.apiRequest(`/api/campaigns/${this.activeCampaignId}/start`, "POST");
      App.showToast(res.message, "success");
      this.refreshDetail();
    } catch (e) {
      console.error(e);
    }
  },

  async stopCampaign() {
    if (!this.activeCampaignId) return;
    try {
      const res = await App.apiRequest(`/api/campaigns/${this.activeCampaignId}/stop`, "POST");
      App.showToast(res.message, "info");
      this.refreshDetail();
    } catch (e) {
      console.error(e);
    }
  },

  async retryFailed() {
    if (!this.activeCampaignId) return;
    try {
      const res = await App.apiRequest(`/api/campaigns/${this.activeCampaignId}/retry-failed`, "POST");
      App.showToast(res.message, "info");
      this.refreshDetail();
    } catch (e) {
      console.error(e);
    }
  },

  async deleteCampaign(id) {
    if (confirm(`Are you sure you want to permanently delete Campaign #${id} and its message delivery history? (Your Google Sheet and recipient list will not be touched).`)) {
      try {
        const res = await App.apiRequest(`/api/campaigns/${id}`, "DELETE");
        App.showToast(res.message, "info");
        if (this.activeCampaignId === id) {
          this.activeCampaignId = null;
          document.getElementById("campaign-detail-card").style.display = "none";
        }
        this.selectedCampaignIds.delete(id);
        this.updateBulkDeleteUI();
        this.loadCampaigns();
        Dashboard.loadStats();
      } catch (e) {
        console.error(e);
      }
    }
  },

  deleteCurrentCampaign() {
    if (this.activeCampaignId) {
      this.deleteCampaign(this.activeCampaignId);
    }
  },

  async bulkDelete() {
    const ids = Array.from(this.selectedCampaignIds);
    if (!ids.length) return;
    if (confirm(`Permanently delete ${ids.length} selected campaigns? (Your Google Sheet will not be modified).`)) {
      try {
        const res = await App.apiRequest("/api/campaigns/bulk-delete", "POST", { campaign_ids: ids });
        App.showToast(res.message, "info");
        this.selectedCampaignIds.clear();
        this.updateBulkDeleteUI();
        document.getElementById("campaign-detail-card").style.display = "none";
        this.loadCampaigns();
        Dashboard.loadStats();
      } catch (e) {
        console.error(e);
      }
    }
  }
};
