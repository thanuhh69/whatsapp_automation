// WhatsApp Module
const WhatsApp = {
  init() {
    this.bindEvents();
    this.checkStatus();
  },

  bindEvents() {
    const connectBtn = document.getElementById("wa-connect-btn");
    const disconnectBtn = document.getElementById("wa-disconnect-btn");
    const checkBtn = document.getElementById("wa-check-status-btn");
    const sendRealTestBtn = document.getElementById("send-real-test-wa-btn");

    if (connectBtn) connectBtn.addEventListener("click", () => this.connect());
    if (disconnectBtn) disconnectBtn.addEventListener("click", () => this.disconnect());
    if (checkBtn) checkBtn.addEventListener("click", () => this.checkStatus());
    if (sendRealTestBtn) sendRealTestBtn.addEventListener("click", () => this.sendRealTestMessage());
  },

  async checkStatus() {
    try {
      const data = await App.apiRequest("/api/whatsapp/status");
      this.updateUI(data.status);
    } catch (e) {
      this.updateUI("unknown");
    }
  },

  updateUI(status) {
    const circle = document.getElementById("wa-large-status-circle");
    const text = document.getElementById("wa-large-status-text");

    if (circle && text) {
      circle.className = `status-indicator-circle ${status}`;
      text.textContent = status.toUpperCase();
    }

    Dashboard.loadStats();
  },

  async connect() {
    App.showToast("Opening WhatsApp Web in visible browser window... Scan QR Code when prompted.", "info");
    this.updateUI("connecting");
    try {
      const res = await App.apiRequest("/api/whatsapp/connect", "POST");
      App.showToast(res.message, res.status === "connected" ? "success" : "info");
      this.updateUI(res.status);
    } catch (e) {
      this.updateUI("disconnected");
    }
  },

  async disconnect() {
    try {
      const res = await App.apiRequest("/api/whatsapp/disconnect", "POST");
      App.showToast(res.message, "info");
      this.updateUI("disconnected");
    } catch (e) {
      console.error(e);
    }
  },

  async sendRealTestMessage() {
    const phone = document.getElementById("test-wa-phone").value.trim();
    const message = document.getElementById("test-wa-message").value.trim();

    if (!phone || !message) {
      App.showToast("Please enter both a test phone number and a test message.", "error");
      return;
    }

    const box = document.getElementById("test-wa-status-box");
    const stepsList = document.getElementById("test-wa-steps-list");
    if (box) box.style.display = "block";
    if (stepsList) {
      stepsList.innerHTML = `<li>Verifying WhatsApp Web connection status...</li>`;
    }

    try {
      const res = await App.apiRequest("/api/whatsapp/test-send", "POST", { phone, message });
      if (stepsList && res.steps) {
        stepsList.innerHTML = res.steps.map(s => `<li>${s}</li>`).join("");
      }

      if (res.success) {
        App.showToast("Real WhatsApp Test message delivered successfully!", "success");
      } else {
        App.showToast(`Real WhatsApp Test failed: ${res.error}`, "error");
        if (stepsList) {
          stepsList.innerHTML += `<li style="color: var(--accent-red); font-weight:600;">Failed: ${res.error}</li>`;
        }
      }
    } catch (e) {
      if (stepsList) {
        stepsList.innerHTML += `<li style="color: var(--accent-red); font-weight:600;">Execution Error: ${e.message}</li>`;
      }
    }
  }
};
