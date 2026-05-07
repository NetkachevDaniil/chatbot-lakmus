async function checkExistingSession() {
  try {
    const response = await fetch("/api/auth/status", { credentials: "same-origin" });
    if (response.ok) {
      window.location.href = "/workspace";
    }
  } catch (_) {
    // Keep the user on the login page when the check fails.
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const message = document.getElementById("login-message");
  const submitButton = form.querySelector("button[type='submit']");
  message.textContent = "Проверка учетных данных...";
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({
        username: formData.get("username"),
        password: formData.get("password"),
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Не удалось войти");
    }

    message.textContent = "Сессия создана. Переход в рабочую область...";
    window.location.href = "/workspace";
  } catch (error) {
    message.textContent = error.message;
    submitButton.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  checkExistingSession();
  const form = document.getElementById("login-form");
  form?.addEventListener("submit", handleLogin);
});
