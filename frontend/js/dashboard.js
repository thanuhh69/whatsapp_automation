// Dashboard Module
const Dashboard = {
  init() {
    this.loadStats();
    this.bindQuickActions();
    // Refresh stats periodically
    setInterval(() => this.loadStats(), 15000);
  },

  async loadStats() {
    try {
      const stats = await App.apiRequest("/api/dashboard/stats");
      
      document.getElementById("kpi-total-registrants").textContent = stats.total_registrants;
      document.getElementById("kpi-eligible-recipients").textContent = stats.eligible_recipients;
      document.getElementById("kpi-total-campaigns").textContent = stats.total_campaigns;
      document.getElementById("kpi-opt-out-count").textContent = stats.opt_out_count;

      // Update header WhatsApp status pill
      const pill = document.getElementById("header-wa-status");
      if (pill) {
        const dot = pill.querySelector(".status-dot");
        const label = pill.querySelector(".status-label");
        
        dot.className = `status-dot ${stats.whatsapp_status}`;
        label.textContent = `WhatsApp: ${stats.whatsapp_status.toUpperCase()}`;
      }

      // Test mode badge
      const badge = document.getElementById("test-mode-badge");
      if (badge) {
        if (stats.test_mode_enabled) {
          badge.style.display = "flex";
        } else {
          badge.style.display = "none";
        }
      }

    } catch (err) {
      console.error("Dashboard stats failed to load:", err);
    }
  },

  bindQuickActions() {
    const connBtn = document.getElementById("dash-btn-connect-wa");
    if (connBtn) {
      connBtn.addEventListener("click", () => {
        document.getElementById("nav-whatsapp").click();
      });
    }

    const newCampBtn = document.getElementById("dash-btn-new-campaign");
    if (newCampBtn) {
      newCampBtn.addEventListener("click", () => {
        document.getElementById("nav-campaigns").click();
        document.getElementById("open-create-campaign-modal").click();
      });
    }
  }
};
