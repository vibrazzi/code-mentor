const form = document.getElementById("chatForm");
const input = document.getElementById("userInput");
const sendButton = document.getElementById("sendButton");
const messagesContainer = document.getElementById("chatMessages");
const typingIndicator = document.getElementById("typingIndicator");
const suggestionButtons = document.querySelectorAll("[data-example]");

const conversationHistory = [];
const HISTORY_PAYLOAD_LIMIT = 6;
const HISTORY_STORE_LIMIT = 12;

function setLoading(isLoading) {
    if (isLoading) {
        typingIndicator.classList.add("typing-indicator--visible");
        sendButton.disabled = true;
        input.setAttribute("aria-busy", "true");
    } else {
        typingIndicator.classList.remove("typing-indicator--visible");
        input.removeAttribute("aria-busy");
        if (input.value.trim().length > 0) {
            sendButton.disabled = false;
        }
    }
}

function formatMessageContent(text, role) {
    const div = document.createElement("div");

    if (role === "assistant" || role === "system") {
        const rawHTML = marked.parse(text, {
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false
        });
        div.innerHTML = DOMPurify.sanitize(rawHTML);
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

function createMessageElement(text, role) {
    const wrapper = document.createElement("div");
    wrapper.className = `chat-message chat-message--${role}`;

    const avatar = document.createElement("div");
    avatar.className = "chat-message__avatar";
    avatar.textContent = role === "user" ? "👤" : role === "assistant" ? "🤖" : "⚠️";

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
        conversationHistory.splice(0, conversationHistory.length - HISTORY_STORE_LIMIT);
    }

    const payload = {
        message,
        history: conversationHistory.slice(0, -1).slice(-HISTORY_PAYLOAD_LIMIT),
    };

    const assistantMessageElement = createMessageElement("", "assistant");
    messagesContainer.appendChild(assistantMessageElement);

    const contentDiv = assistantMessageElement.querySelector(".chat-message__content");
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
            throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                if (buffer.trim()) {
                    console.warn("Stream terminou com dados restantes no buffer:", buffer);
                }
                break;
            }

            buffer += decoder.decode(value, { stream: true });

            let lines = buffer.split('\n');
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
                            contentDiv.appendChild(formatMessageContent(accumulatedText, "assistant"));
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }
                    } catch (parseError) {
                        console.error("Erro ao parsear linha SSE:", trimmedLine, parseError);
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
        if (!accumulatedText.trim()) {
            assistantMessageElement.remove();
        }

        appendMessage(
            `❌ Ops! Algo deu errado.\n${error.message}\n\nVerifique se o servidor Ollama está em execução e tente novamente.`,
            "system",
        );
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

form.addEventListener("submit", handleFormSubmit);
input.addEventListener("input", handleInputChange);
suggestionButtons.forEach((button) => button.addEventListener("click", handleSuggestionClick));

input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        form.requestSubmit();
    }
});
