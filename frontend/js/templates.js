// Templates Module
const Templates = {
  templates: [],

  init() {
    this.bindEvents();
    this.loadTemplates();
  },

  bindEvents() {
    const select = document.getElementById("template-select");
    if (select) {
      select.addEventListener("change", (e) => {
        const id = e.target.value;
        const tpl = this.templates.find(t => t.id === id);
        if (tpl) {
          document.getElementById("template-name-input").value = tpl.name;
          document.getElementById("template-content-input").value = tpl.content;
          this.updatePreview();
        }
      });
    }

    const contentInput = document.getElementById("template-content-input");
    const nameInput = document.getElementById("template-name-input");
    if (contentInput) contentInput.addEventListener("input", () => this.updatePreview());
    if (nameInput) nameInput.addEventListener("input", () => this.updatePreview());

    // Variable insertion pills
    document.querySelectorAll(".pill-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const varText = btn.getAttribute("data-var");
        const textarea = document.getElementById("template-content-input");
        if (textarea) {
          const start = textarea.selectionStart;
          const end = textarea.selectionEnd;
          const text = textarea.value;
          textarea.value = text.substring(0, start) + varText + text.substring(end);
          textarea.focus();
          textarea.selectionStart = textarea.selectionEnd = start + varText.length;
          this.updatePreview();
        }
      });
    });

    const newBtn = document.getElementById("new-template-btn");
    if (newBtn) {
      newBtn.addEventListener("click", () => {
        document.getElementById("template-select").value = "";
        document.getElementById("template-name-input").value = "New Custom Template";
        document.getElementById("template-content-input").value = "Hello {{name}}, ";
        this.updatePreview();
      });
    }

    const saveBtn = document.getElementById("save-template-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => this.saveTemplate());
    }

    const deleteBtn = document.getElementById("delete-template-btn");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", () => this.deleteTemplate());
    }

    const useInCampBtn = document.getElementById("create-campaign-from-composer");
    if (useInCampBtn) {
      useInCampBtn.addEventListener("click", () => {
        const text = document.getElementById("template-content-input").value;
        const name = document.getElementById("template-name-input").value;
        document.getElementById("nav-campaigns").click();
        document.getElementById("open-create-campaign-modal").click();

        document.getElementById("modal-campaign-name").value = name ? `${name} Campaign` : "New Campaign";
        document.getElementById("modal-campaign-template-text").value = text;
      });
    }
  },

  async loadTemplates() {
    try {
      this.templates = await App.apiRequest("/api/templates");
      const select = document.getElementById("template-select");
      const modalSelect = document.getElementById("modal-campaign-template-select");

      if (select) {
        select.innerHTML = '<option value="">-- Choose Template --</option>' +
          this.templates.map(t => `<option value="${t.id}">${t.name}</option>`).join("");

        if (this.templates.length > 0) {
          select.value = this.templates[0].id;
          document.getElementById("template-name-input").value = this.templates[0].name;
          document.getElementById("template-content-input").value = this.templates[0].content;
        }
      }

      if (modalSelect) {
        modalSelect.innerHTML = '<option value="">Custom Message</option>' +
          this.templates.map(t => `<option value="${t.id}">${t.name}</option>`).join("");
      }

      this.updatePreview();
    } catch (e) {
      console.error(e);
    }
  },

  updatePreview() {
    const text = document.getElementById("template-content-input").value;
    const previewEl = document.getElementById("preview-message-text");

    let rendered = text
      .replace(/\{\{\s*name\s*\}\}/g, "John Doe")
      .replace(/\{\{\s*email\s*\}\}/g, "john@q9x.org");

    if (previewEl) {
      previewEl.textContent = rendered || "Your rendered message preview...";
    }
  },

  async saveTemplate() {
    const name = document.getElementById("template-name-input").value;
    const content = document.getElementById("template-content-input").value;
    const selectedId = document.getElementById("template-select").value;

    if (!name || !content) {
      App.showToast("Please provide both template name and message content.", "error");
      return;
    }

    try {
      if (selectedId && selectedId.startsWith("tpl_")) {
        await App.apiRequest(`/api/templates/${selectedId}`, "PUT", { name, content });
        App.showToast("Template updated successfully!", "success");
      } else {
        await App.apiRequest("/api/templates", "POST", { name, content });
        App.showToast("New template created!", "success");
      }
      this.loadTemplates();
    } catch (e) {
      console.error(e);
    }
  },

  async deleteTemplate() {
    const selectedId = document.getElementById("template-select").value;
    if (!selectedId) {
      App.showToast("No template selected to delete.", "error");
      return;
    }

    try {
      await App.apiRequest(`/api/templates/${selectedId}`, "DELETE");
      App.showToast("Template deleted.", "info");
      this.loadTemplates();
    } catch (e) {
      console.error(e);
    }
  }
};
