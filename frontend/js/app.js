// Core App Module
const App = {
  token: localStorage.getItem("q9x_bearer_token") || "",

  init() {
    this.bindNavigation();
    this.bindTokenAuth();
    this.bindGlobalSync();
    this.bindSettingsForm();
    this.bindAdminResets();

    const tokenInput = document.getElementById("auth-token-input");
    if (tokenInput && this.token) {
      tokenInput.value = this.token;
    }
  },

  bindNavigation() {
    const navButtons = document.querySelectorAll(".nav-item");
    const views = document.querySelectorAll(".view-section");
    const pageTitle = document.getElementById("page-title");
    const pageSub = document.getElementById("page-subtitle");

    const titleMap = {
      "dashboard-view": { title: "Dashboard Overview", sub: "Real-time status of Q9X WhatsApp communication pipeline" },
      "recipients-view": { title: "Registrants & Recipients", sub: "Manage eligible recipients synced from Google Sheets" },
      "templates-view": { title: "Composer & Templates", sub: "Create personalized message templates with variables" },
      "campaigns-view": { title: "Campaign Operations", sub: "Launch, monitor, and control communication campaigns" },
      "whatsapp-view": { title: "WhatsApp Web Connection", sub: "Authenticate persistent Chromium browser session" },
      "optouts-view": { title: "Opt-Out Management", sub: "Maintain explicit opt-out registry and auto-keyword list" },
      "settings-view": { title: "System Settings", sub: "Configure delays, column mappings, and test mode" }
    };

    navButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetViewId = btn.getAttribute("data-tab");
        
        navButtons.forEach(b => b.classList.remove("active"));
        views.forEach(v => v.classList.remove("active"));

        btn.classList.add("active");
        const targetView = document.getElementById(targetViewId);
        if (targetView) targetView.classList.add("active");

        if (titleMap[targetViewId]) {
          pageTitle.textContent = titleMap[targetViewId].title;
          pageSub.textContent = titleMap[targetViewId].sub;
        }

        // Trigger view-specific loads
        if (targetViewId === "dashboard-view") Dashboard.loadStats();
        if (targetViewId === "recipients-view") Recipients.loadRecipients();
        if (targetViewId === "templates-view") Templates.loadTemplates();
        if (targetViewId === "campaigns-view") Campaigns.loadCampaigns();
        if (targetViewId === "whatsapp-view") WhatsApp.checkStatus();
        if (targetViewId === "optouts-view") OptOuts.loadOptOuts();
        if (targetViewId === "settings-view") App.loadSettings();
      });
    });
  },

  bindTokenAuth() {
    const saveBtn = document.getElementById("save-token-btn");
    const tokenInput = document.getElementById("auth-token-input");
    const headerTokenBtn = document.getElementById("header-token-btn");

    const promptForToken = () => {
      const input = prompt("Enter API Security Token:", this.token);
      if (input !== null) {
        this.token = this.cleanToken(input);
        localStorage.setItem("q9x_bearer_token", this.token);
        if (tokenInput) tokenInput.value = this.token;
        this.showToast("API Bearer Token saved successfully!", "success");
      }
    };

    if (headerTokenBtn) {
      headerTokenBtn.addEventListener("click", promptForToken);
    }

    if (saveBtn && tokenInput) {
      saveBtn.addEventListener("click", () => {
        this.token = this.cleanToken(tokenInput.value);
        localStorage.setItem("q9x_bearer_token", this.token);
        this.showToast("API Bearer Token saved successfully!", "success");
      });
    }
  },

  bindGlobalSync() {
    const quickSyncBtn = document.getElementById("quick-sync-btn");
    if (quickSyncBtn) {
      quickSyncBtn.addEventListener("click", async () => {
        await Recipients.triggerSync();
      });
    }
  },

  cleanToken(str) {
    if (!str) return "";
    return String(str).replace(/[^a-zA-Z0-9]/g, "").trim();
  },

  async apiRequest(endpoint, method = "GET", body = null) {
    const headers = { "Content-Type": "application/json" };
    const tok = this.cleanToken(this.token || localStorage.getItem("q9x_bearer_token"));
    if (tok) {
      headers["Authorization"] = `Bearer ${tok}`;
    }

    const config = { method, headers };
    if (body) config.body = JSON.stringify(body);

    try {
      const response = await fetch(endpoint, config);
      const data = await response.json();
      if (!response.ok) {
        if ((response.status === 401 || response.status === 403) && method !== "GET") {
          const input = prompt("API Security Token required for mutating actions. Please enter token:", this.token);
          if (input) {
            this.token = this.cleanToken(input);
            localStorage.setItem("q9x_bearer_token", this.token);
            headers["Authorization"] = `Bearer ${this.token}`;
            const retryConfig = { method, headers };
            if (body) retryConfig.body = JSON.stringify(body);
            const retryResp = await fetch(endpoint, retryConfig);
            const retryData = await retryResp.json();
            if (!retryResp.ok) throw new Error(retryData.detail || "API Request Failed");
            return retryData;
          }
        }
        throw new Error(data.detail || "API Request Failed");
      }
      return data;
    } catch (err) {
      this.showToast(err.message, "error");
      throw err;
    }
  },

  showToast(message, type = "info") {
    if (!message) return;
    const msgStr = String(message);
    if (msgStr.includes("did not match the expected pattern") || msgStr.includes("SyntaxError")) {
      return;
    }
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = msgStr;

    container.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 4000);
  },

  formatDate(dateStr, timeOnly = false) {
    if (!dateStr) return "-";
    const str = String(dateStr).trim();
    if (str.includes(",") || /AM|PM/i.test(str)) {
      return str;
    }
    try {
      let isoStr = str;
      if (/^\d{4}-\d{2}-\d{2}/.test(isoStr)) {
        isoStr = isoStr.replace(" ", "T");
      }
      if (!isoStr.endsWith("Z") && !isoStr.includes("+")) {
        isoStr += "Z";
      }
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return str;
      return timeOnly ? d.toLocaleTimeString() : d.toLocaleString();
    } catch (e) {
      return str;
    }
  },

  async loadSettings() {
    try {
      const data = await this.apiRequest("/api/settings");
      document.getElementById("cfg-sheet-id").value = data.GOOGLE_SHEET_ID || "";
      document.getElementById("cfg-worksheet-name").value = data.GOOGLE_WORKSHEET_NAME || "";
      document.getElementById("cfg-min-delay").value = data.MIN_DELAY_SECONDS;
      document.getElementById("cfg-max-delay").value = data.MAX_DELAY_SECONDS;
      document.getElementById("cfg-optout-keywords").value = data.OPT_OUT_KEYWORDS || "";
      document.getElementById("cfg-poll-interval").value = data.INBOX_POLL_INTERVAL_SECONDS;
      document.getElementById("cfg-test-mode").checked = data.TEST_MODE;

      await this.fetchSheetHeaders(data);
    } catch (e) {
      console.error(e);
    }
  },

  async fetchSheetHeaders(settingsData = null) {
    try {
      const res = await this.apiRequest("/api/settings/sheet-headers");
      const headers = res.headers || [];
      const populateDropdown = (elemId, selectedVal, fallbackDefault) => {
        const select = document.getElementById(elemId);
        if (!select) return;
        const currentVal = selectedVal || fallbackDefault;
        select.innerHTML = headers.map(h => `<option value="${h}" ${h.toLowerCase() === currentVal.toLowerCase() ? 'selected' : ''}>${h}</option>`).join('');
        if (!headers.length) {
          select.innerHTML = `<option value="${currentVal}">${currentVal}</option>`;
        }
      };

      const s = settingsData || {};
      populateDropdown("cfg-map-name", s.COLUMN_MAP_NAME, "Name");
      populateDropdown("cfg-map-phone", s.COLUMN_MAP_PHONE, "Mobile");
      populateDropdown("cfg-map-email", s.COLUMN_MAP_EMAIL, "Email");
      populateDropdown("cfg-map-consent", s.COLUMN_MAP_CONSENT, "WhatsApp Consent");
    } catch (err) {
      console.log("Sheet headers not fetched yet or sheet offline.");
    }
  },

  bindSettingsForm() {
    const form = document.getElementById("settings-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
          GOOGLE_SHEET_ID: document.getElementById("cfg-sheet-id").value,
          GOOGLE_WORKSHEET_NAME: document.getElementById("cfg-worksheet-name").value,
          COLUMN_MAP_NAME: document.getElementById("cfg-map-name").value,
          COLUMN_MAP_PHONE: document.getElementById("cfg-map-phone").value,
          COLUMN_MAP_EMAIL: document.getElementById("cfg-map-email").value,
          COLUMN_MAP_CONSENT: document.getElementById("cfg-map-consent").value,
          MIN_DELAY_SECONDS: parseInt(document.getElementById("cfg-min-delay").value, 10),
          MAX_DELAY_SECONDS: parseInt(document.getElementById("cfg-max-delay").value, 10),
          OPT_OUT_KEYWORDS: document.getElementById("cfg-optout-keywords").value,
          INBOX_POLL_INTERVAL_SECONDS: parseInt(document.getElementById("cfg-poll-interval").value, 10),
          TEST_MODE: document.getElementById("cfg-test-mode").checked
        };
        try {
          const res = await this.apiRequest("/api/settings", "PUT", payload);
          document.getElementById("cfg-sheet-id").value = res.GOOGLE_SHEET_ID;
          this.showToast("Settings and Column Mappings saved successfully!", "success");
        } catch (err) {
          console.error(err);
        }
      });
    }

    const testConnBtn = document.getElementById("cfg-test-connection-btn");
    if (testConnBtn) {
      testConnBtn.addEventListener("click", async () => {
        try {
          const res = await this.apiRequest("/api/settings/test-connection", "POST");
          this.showToast(res.message, "success");
        } catch (err) {
          console.error(err);
        }
      });
    }

    const fetchHeadersBtn = document.getElementById("cfg-fetch-headers-btn");
    if (fetchHeadersBtn) {
      fetchHeadersBtn.addEventListener("click", async () => {
        await this.fetchSheetHeaders();
        this.showToast("Google Sheet headers fetched successfully!", "info");
      });
    }

    const deleteCredsBtn = document.getElementById("delete-credentials-btn");
    if (deleteCredsBtn) {
      deleteCredsBtn.addEventListener("click", async () => {
        if (confirm("Are you sure you want to delete your saved Google Service Account credentials JSON file and reset the Google Sheet configuration?")) {
          try {
            const res = await this.apiRequest("/api/settings/credentials", "DELETE");
            this.showToast(res.message, "info");
            this.loadSettings();
          } catch (err) {
            console.error(err);
          }
        }
      });
    }
  },

  bindAdminResets() {
    const bindReset = (btnId, resetType, confirmMsg) => {
      const btn = document.getElementById(btnId);
      if (btn) {
        btn.addEventListener("click", async () => {
          if (confirm(confirmMsg)) {
            try {
              const res = await this.apiRequest("/api/settings/admin-reset", "POST", { reset_type: resetType });
              this.showToast(res.message, "success");
              Dashboard.loadStats();
              if (resetType === "recipients" || resetType === "full_database") Recipients.loadRecipients();
              if (resetType === "campaigns" || resetType === "full_database") Campaigns.loadCampaigns();
            } catch (err) {
              console.error(err);
            }
          }
        });
      }
    };

    bindReset("admin-reset-recipients-btn", "recipients", "Clear all local recipients from local SQLite database? (Your Google Sheet will not be modified).");
    bindReset("admin-reset-campaigns-btn", "campaigns", "Clear all campaign history and message delivery logs?");
    bindReset("admin-reset-messages-btn", "messages", "Clear message delivery logs?");
    bindReset("admin-reset-full-btn", "full_database", "WARNING: Reset entire local database? All recipients, campaigns, logs, and opt-outs will be cleared cleanly.");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  App.init();
  Dashboard.init();
  Recipients.init();
  Templates.init();
  Campaigns.init();
  WhatsApp.init();
  OptOuts.init();
});
