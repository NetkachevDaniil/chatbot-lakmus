const state = {
  chats: [],
  activeChatId: null,
};

function formatTime(value) {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatMessageText(text) {
  return escapeHtml(text).replaceAll("\n", "<br>");
}

function renderChats() {
  const list = document.getElementById("chat-list");
  const count = document.getElementById("chat-count");
  count.textContent = `${state.chats.length}`;
  list.innerHTML = state.chats
    .map(
      (chat) => `
        <article class="chat-list-item ${chat.id === state.activeChatId ? "active" : ""}" data-chat-id="${chat.id}">
          <button class="chat-list-main" data-chat-open="${chat.id}" type="button">
            <span class="chat-list-title">${escapeHtml(chat.title)}</span>
            <span class="chat-list-time">${formatTime(chat.updated_at)}</span>
          </button>
          <button class="chat-delete-button" data-chat-delete="${chat.id}" type="button" aria-label="Удалить чат">
            Удалить
          </button>
        </article>
      `,
    )
    .join("");

  list.querySelectorAll("[data-chat-open]").forEach((button) => {
    button.addEventListener("click", () => {
      loadChat(button.dataset.chatOpen);
    });
  });

  list.querySelectorAll("[data-chat-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      const chatId = button.dataset.chatDelete;
      const confirmed = window.confirm("Удалить этот чат из истории?");
      if (!confirmed) {
        return;
      }
      await deleteChat(chatId);
    });
  });
}

function renderMessages(chat) {
  const messages = document.getElementById("messages");
  const title = document.getElementById("chat-title");
  title.textContent = chat.title;
  messages.innerHTML = chat.messages
    .map((message) => {
      const responseJson = message.meta?.response_json
        ? `<pre class="json-block">${escapeHtml(JSON.stringify(message.meta.response_json, null, 2))}</pre>`
        : "";
      const diagram = message.meta?.diagram
        ? `<pre class="json-block">${escapeHtml(message.meta.diagram)}</pre>`
        : "";
      const fileBadge = message.file_name
        ? `<span class="message-file">${escapeHtml(message.file_name)}</span>`
        : "";
      const statusBadge =
        message.status === "pending"
          ? '<span class="message-status">Ожидание ответа…</span>'
          : "";

      return `
        <article class="message ${message.role}">
          <div class="message-meta">
            <span>${message.role === "user" ? "Вы" : "Лакмус"}</span>
            <span>${formatTime(message.created_at)}</span>
          </div>
          <div class="message-body">
            <p>${formatMessageText(message.content)}</p>
            ${fileBadge}
            ${statusBadge}
            ${diagram}
            ${responseJson}
          </div>
        </article>
      `;
    })
    .join("");
  messages.scrollTop = messages.scrollHeight;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { credentials: "same-origin", ...options });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Authentication required");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Request failed");
  }
  return response.json();
}

async function refreshChats(preferredChatId = null) {
  const data = await fetchJson("/api/chats");
  state.chats = data.items;
  if (!state.activeChatId) {
    state.activeChatId = preferredChatId || state.chats[0]?.id || null;
  }
  if (preferredChatId) {
    state.activeChatId = preferredChatId;
  }
  renderChats();
}

async function loadChat(chatId) {
  if (!chatId) {
    return null;
  }
  state.activeChatId = chatId;
  renderChats();
  const data = await fetchJson(`/api/chats/${chatId}`);
  renderMessages(data.chat);
  return data.chat;
}

async function createChat() {
  const data = await fetchJson("/api/chats", { method: "POST" });
  await refreshChats(data.chat.id);
  await loadChat(data.chat.id);
}

async function deleteChat(chatId) {
  const statusNode = document.getElementById("composer-status");
  statusNode.textContent = "Удаляем чат...";
  const data = await fetchJson(`/api/chats/${chatId}`, { method: "DELETE" });
  state.chats = data.remaining;

  if (!state.chats.length) {
    state.activeChatId = null;
    renderChats();
    await createChat();
    statusNode.textContent = "Создан новый пустой чат.";
    return;
  }

  if (state.activeChatId === chatId) {
    state.activeChatId = state.chats[0].id;
  }

  renderChats();
  await loadChat(state.activeChatId);
  statusNode.textContent = "Чат удален.";
}

async function pollChat(chatId) {
  const statusNode = document.getElementById("composer-status");

  while (true) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const chat = await loadChat(chatId);
    await refreshChats(chatId);

    const hasPendingMessage = chat.messages.some(
      (message) => message.role === "assistant" && message.status === "pending",
    );

    if (!hasPendingMessage) {
      const lastAssistant = [...chat.messages]
        .reverse()
        .find((message) => message.role === "assistant");
      statusNode.textContent =
        lastAssistant?.status === "error" ? "Сервис вернул ошибку." : "Ответ получен.";
      return;
    }

    statusNode.textContent = "Ожидание ответа от сервиса Б...";
  }
}

async function sendMessage(event) {
  event.preventDefault();
  const promptInput = document.getElementById("prompt-input");
  const fileInput = document.getElementById("file-input");
  const sendButton = document.getElementById("send-button");
  const statusNode = document.getElementById("composer-status");

  if (!state.activeChatId) {
    await createChat();
  }

  if (!promptInput.value.trim()) {
    statusNode.textContent = "Введите промпт.";
    return;
  }

  if (!fileInput.files[0]) {
    statusNode.textContent = "Прикрепите файл для отправки в сервис А.";
    return;
  }

  const formData = new FormData();
  formData.append("prompt", promptInput.value);
  formData.append("file", fileInput.files[0]);

  sendButton.disabled = true;
  statusNode.textContent = "Отправка запроса...";

  try {
    const data = await fetchJson(`/api/chats/${state.activeChatId}/messages`, {
      method: "POST",
      body: formData,
    });

    renderMessages(data.chat);
    await refreshChats(state.activeChatId);
    promptInput.value = "";
    fileInput.value = "";
    document.getElementById("file-name").textContent = "Файл не выбран";

    await pollChat(state.activeChatId);
  } catch (error) {
    statusNode.textContent = error.message;
    await loadChat(state.activeChatId);
  } finally {
    sendButton.disabled = false;
  }
}

async function logout() {
  await fetchJson("/api/auth/logout", { method: "POST" });
  window.location.href = "/login";
}

function handleFileChange(event) {
  const name = event.target.files[0]?.name || "Файл не выбран";
  document.getElementById("file-name").textContent = name;
}

async function bootstrapWorkspace() {
  await fetchJson("/api/auth/status");
  const root = document.querySelector(".workspace");
  const urlChatId = new URLSearchParams(window.location.search).get("chat");
  state.activeChatId = urlChatId || root.dataset.initialChatId;
  await refreshChats(state.activeChatId);
  if (state.activeChatId) {
    await loadChat(state.activeChatId);
  }

  document.getElementById("new-chat-button").addEventListener("click", createChat);
  document.getElementById("composer").addEventListener("submit", sendMessage);
  document.getElementById("logout-button").addEventListener("click", logout);
  document.getElementById("file-input").addEventListener("change", handleFileChange);
}

document.addEventListener("DOMContentLoaded", () => {
  bootstrapWorkspace().catch((error) => {
    const statusNode = document.getElementById("composer-status");
    if (statusNode) {
      statusNode.textContent = error.message;
    }
  });
});
