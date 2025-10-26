const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const sendButton = document.getElementById("sendButton");
const messagesContainer = document.getElementById("chatMessages");
const typingIndicator = document.getElementById("typingIndicator");
const suggestionButtons = document.querySelectorAll("[data-example]");
const clearChatButton = document.getElementById("clearChatButton");
const clearModal = document.getElementById("clearModal");
const modalCancel = document.getElementById("modalCancel");
const modalConfirm = document.getElementById("modalConfirm");

const conversationHistory = [];
const HISTORY_PAYLOAD_LIMIT = 3;
const HISTORY_STORE_LIMIT = 12;

function setLoading(isLoading) {
  if (isLoading) {
    typingIndicator.classList.add("typing-indicator--visible");
    sendButton.disabled = true;
    input.setAttribute("aria-busy", "true");
  } else {
    typingIndicator.classList.remove("typing-indicator--visible");
    input.removeAttribute("aria-busy");
    sendButton.disabled = false;
  }
}

function formatMessageContent(text, role) {
  const div = document.createElement("div");

  if (role === "assistant" || role === "system") {
    const rawHTML = marked.parse(text, {
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false,
    });
    div.innerHTML = DOMPurify.sanitize(rawHTML);
    addCopyButtonsToCodeBlocks(div);
  } else {
    const lines = text.split(/\r?\n/);
    lines.forEach((line, index) => {
      if (index > 0) {
        div.appendChild(document.createElement("br"));
      }
      div.appendChild(document.createTextNode(line));
    });
  }

  return div;
}

function addCopyButtonsToCodeBlocks(container) {
  const codeBlocks = container.querySelectorAll("pre code");

  codeBlocks.forEach((codeBlock) => {
    const pre = codeBlock.parentElement;
    if (!pre || pre.querySelector(".code-copy-button")) return;

    const button = document.createElement("button");
    button.className = "code-copy-button";
    button.innerHTML = "Copiar";
    button.setAttribute("aria-label", "Copiar código");

    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(codeBlock.textContent);
        button.innerHTML = "✅ Copiado!";
        button.classList.add("copied");

        setTimeout(() => {
          button.innerHTML = "Copiar";
          button.classList.remove("copied");
        }, 2000);
      } catch (err) {
        console.error("Erro ao copiar:", err);
        button.innerHTML = "❌ Erro";
        setTimeout(() => {
          button.innerHTML = "Copiar";
        }, 2000);
      }
    });

    pre.style.position = "relative";
    pre.appendChild(button);
  });
}

function createMessageElement(text, role) {
  const wrapper = document.createElement("div");
  wrapper.className = `chat-message chat-message--${role}`;

  const avatar = document.createElement("div");
  avatar.className = "chat-message__avatar";
  avatar.textContent =
    role === "user" ? "👤" : role === "assistant" ? "🤖" : "⚠️";

  const content = document.createElement("div");
  content.className = "chat-message__content";
  content.appendChild(formatMessageContent(text, role));

  if (role === "user") {
    wrapper.appendChild(content);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(content);
  }

  return wrapper;
}

function appendMessage(text, role = "assistant") {
  const element = createMessageElement(text, role);
  messagesContainer.appendChild(element);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendMessage(message) {
  conversationHistory.push({ role: "user", content: message });

  if (conversationHistory.length > HISTORY_STORE_LIMIT) {
    conversationHistory.splice(
      0,
      conversationHistory.length - HISTORY_STORE_LIMIT
    );
  }

  const payload = {
    message,
    history: conversationHistory.slice(0, -1).slice(-HISTORY_PAYLOAD_LIMIT),
  };

  const assistantMessageElement = createMessageElement("", "assistant");
  messagesContainer.appendChild(assistantMessageElement);

  const contentDiv = assistantMessageElement.querySelector(
    ".chat-message__content"
  );
  let accumulatedText = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const data = await response.json();
      const detail = data?.detail ?? "Erro inesperado ao gerar resposta.";
      throw new Error(
        typeof detail === "string" ? detail : JSON.stringify(detail)
      );
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        if (buffer.trim()) {
          console.warn(
            "Stream terminou com dados restantes no buffer:",
            buffer
          );
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      let lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        const trimmedLine = line.trim();

        if (!trimmedLine) continue;

        if (trimmedLine.startsWith("data: ")) {
          const dataStr = trimmedLine.slice(6).trim();

          if (dataStr === "[DONE]") {
            console.log("Stream marked as DONE.");
            continue;
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (data.error) {
              console.error("Backend error received via stream:", data);
              throw new Error(data.error || "Erro retornado pelo servidor.");
            }

            if (data.chunk) {
              accumulatedText += data.chunk;
              contentDiv.innerHTML = "";
              contentDiv.appendChild(
                formatMessageContent(accumulatedText, "assistant")
              );
              messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
          } catch (parseError) {
            console.error(
              "Erro ao parsear linha SSE:",
              trimmedLine,
              parseError
            );
            console.error("String que falhou:", dataStr);
            throw new Error("Erro ao processar dados da resposta.");
          }
        } else {
          console.warn("Linha SSE inesperada (ignorada):", trimmedLine);
        }
      }
    }

    if (!accumulatedText.trim()) {
      assistantMessageElement.remove();
      throw new Error("Não recebi nenhum conteúdo do mentor.");
    }

    conversationHistory.push({ role: "assistant", content: accumulatedText });
  } catch (error) {
    // Check if error occurred during streaming (partial balloon exists)
    if (
      assistantMessageElement &&
      messagesContainer.contains(assistantMessageElement)
    ) {
      // Reuse existing balloon and convert to error message
      assistantMessageElement.className = "chat-message chat-message--system";
      const avatar = assistantMessageElement.querySelector(
        ".chat-message__avatar"
      );
      const errorContent = assistantMessageElement.querySelector(
        ".chat-message__content"
      );

      if (avatar) avatar.textContent = "⚠️";
      if (errorContent) {
        errorContent.innerHTML = "";
        errorContent.appendChild(
          formatMessageContent(
            `❌ Ops! Algo deu errado durante a resposta.\n${error.message}\n\nNão foi possível obter a resposta completa. Verifique sua conexão ou tente novamente mais tarde.`,
            "system"
          )
        );
      }
    } else {
      appendMessage(
        `❌ Ops! Algo deu errado.\n${error.message}\n\nNão foi possível obter a resposta. Verifique sua conexão ou tente novamente mais tarde.`,
        "system"
      );
    }
  }
}

function handleFormSubmit(event) {
  event.preventDefault();
  const message = input.value.trim();

  if (!message) {
    return;
  }

  appendMessage(message, "user");
  setLoading(true);
  input.value = "";
  sendButton.disabled = true;

  sendMessage(message).finally(() => {
    setLoading(false);
    setTimeout(() => {
      if (input) {
        input.focus();
      }
    }, 10);
  });
}

function handleInputChange({ target }) {
  sendButton.disabled = target.value.trim().length === 0;
}

function handleSuggestionClick({ currentTarget }) {
  const example = currentTarget.dataset.example ?? "";
  if (!example) {
    return;
  }
  input.value = example;
  sendButton.disabled = false;
  input.focus();
}

function handleClearChat() {
  showModal();
}

function showModal() {
  clearModal.setAttribute("aria-hidden", "false");
  clearModal.focus();
}

function hideModal() {
  clearModal.setAttribute("aria-hidden", "true");
}

function confirmClear() {
  hideModal();

  conversationHistory.length = 0;

  const allMessages = messagesContainer.querySelectorAll(".chat-message");
  allMessages.forEach((message, index) => {
    if (index > 0) {
      message.remove();
    }
  });

  messagesContainer.scrollTop = 0;

  input.focus();
}

form.addEventListener("submit", handleFormSubmit);
input.addEventListener("input", handleInputChange);
suggestionButtons.forEach((button) =>
  button.addEventListener("click", handleSuggestionClick)
);
clearChatButton.addEventListener("click", handleClearChat);

modalCancel.addEventListener("click", hideModal);
modalConfirm.addEventListener("click", confirmClear);

clearModal.addEventListener("click", (event) => {
  if (event.target === clearModal || event.target.classList.contains("modal__overlay")) {
    hideModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && clearModal.getAttribute("aria-hidden") === "false") {
    hideModal();
  }
});

input.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.metaKey &&
    !event.ctrlKey
  ) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && clearModal.getAttribute("aria-hidden") === "false") {
    hideModal();
  }
});
