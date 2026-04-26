const API = "/api";
const USER_ID = "default";
let documents = [];
let selectedDocumentId = null;

const qs = (selector) => document.querySelector(selector);
const qsa = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function setMessage(selector, text, isError = false) {
  const node = qs(selector);
  node.textContent = text;
  node.classList.toggle("error", isError);
}

function switchView(name) {
  qsa(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.view === name));
  qsa(".view").forEach((view) => view.classList.toggle("active", view.id === name));
  if (name === "dashboard") loadDashboard();
}

async function checkHealth() {
  try {
    await api("/health");
    qs("#apiStatus").textContent = "API ready";
    qs("#apiStatus").className = "status ok";
  } catch {
    qs("#apiStatus").textContent = "API offline";
    qs("#apiStatus").className = "status error";
  }
}

async function loadDocuments() {
  const data = await api(`/documents?user_id=${USER_ID}`);
  documents = data.documents;
  if (!selectedDocumentId && documents.length) {
    selectedDocumentId = documents[0].id;
  }
  renderDocuments();
  syncDocumentSelects();
}

function renderDocuments() {
  const list = qs("#documents");
  if (!documents.length) {
    list.innerHTML = '<div class="message">No documents uploaded yet.</div>';
    return;
  }
  list.innerHTML = documents
    .map(
      (doc) => `
        <button class="document ${doc.id === selectedDocumentId ? "active" : ""}" data-doc="${doc.id}">
          <strong>${doc.title}</strong>
          <span>${doc.chunk_count} chunks</span>
        </button>
      `,
    )
    .join("");
  qsa("[data-doc]").forEach((button) => {
    button.addEventListener("click", () => {
      selectedDocumentId = button.dataset.doc;
      renderDocuments();
      syncDocumentSelects();
    });
  });
}

function syncDocumentSelects() {
  ["#chatDocument", "#quizDocument"].forEach((selector) => {
    const select = qs(selector);
    select.innerHTML = documents
      .map((doc) => `<option value="${doc.id}">${doc.title}</option>`)
      .join("");
    if (selectedDocumentId) select.value = selectedDocumentId;
    select.onchange = () => {
      selectedDocumentId = select.value;
      renderDocuments();
      syncDocumentSelects();
    };
  });
}

async function uploadPdf(event) {
  event.preventDefault();
  const file = qs("#pdfFile").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  form.append("user_id", USER_ID);
  setMessage("#uploadResult", "Processing PDF and creating embeddings...");
  try {
    const data = await api("/upload", { method: "POST", body: form });
    selectedDocumentId = data.document.id;
    setMessage("#uploadResult", `Processed ${data.document.title}.`);
    await loadDocuments();
  } catch (error) {
    setMessage("#uploadResult", error.message, true);
  }
}

async function askQuestion(event) {
  event.preventDefault();
  const question = qs("#questionInput").value.trim();
  const documentId = qs("#chatDocument").value;
  if (!question || !documentId) return;
  appendChat("You", question);
  qs("#questionInput").value = "";
  try {
    const data = await api("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: USER_ID, document_id: documentId, question }),
    });
    const pages = data.sources.map((source) => `p.${source.page}`).join(", ");
    appendChat("Assistant", `${data.answer}<div class="sources">Sources: ${pages}</div>`);
  } catch (error) {
    appendChat("System", `<span class="error">${error.message}</span>`);
  }
}

function appendChat(role, html) {
  qs("#chatLog").insertAdjacentHTML(
    "beforeend",
    `<div class="chat-item"><span class="role">${role}</span><div>${html}</div></div>`,
  );
}

async function generateQuiz() {
  const documentId = qs("#quizDocument").value;
  if (!documentId) return;
  qs("#quizList").innerHTML = '<div class="message">Generating grounded questions...</div>';
  try {
    const data = await api("/quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: USER_ID,
        document_id: documentId,
        count: Number(qs("#quizCount").value),
      }),
    });
    qs("#adaptiveProfile").textContent = `Difficulty: ${data.profile.difficulty}. Weak topics: ${data.profile.weak_topics.join(", ") || "none yet"}.`;
    renderQuiz(data.questions);
  } catch (error) {
    qs("#quizList").innerHTML = `<div class="error">${error.message}</div>`;
  }
}

function renderQuiz(questions) {
  if (!questions.length) {
    qs("#quizList").innerHTML = '<div class="message">No questions generated.</div>';
    return;
  }
  qs("#quizList").innerHTML = questions.map(renderQuestion).join("");
  qsa(".submit-answer").forEach((button) => {
    button.addEventListener("click", () => submitAnswer(button.dataset.question));
  });
}

function renderQuestion(question) {
  const answerControl =
    question.type === "mcq"
      ? `<div class="options">${question.options
          .map(
            (option) => `
              <label class="option">
                <input type="radio" name="answer-${question.id}" value="${escapeHtml(option)}" />
                <span>${escapeHtml(option)}</span>
              </label>`,
          )
          .join("")}</div>`
      : `<textarea id="answer-${question.id}" placeholder="${question.type === "coding" ? "Define solve(...)" : "Write your answer"}">${question.starter_code || ""}</textarea>`;

  return `
    <article class="question" id="question-${question.id}">
      <span class="meta">${question.type} · ${question.topic} · ${question.difficulty}</span>
      <p>${escapeHtml(question.question)}</p>
      ${answerControl}
      <button class="submit-answer" type="button" data-question="${question.id}">Submit answer</button>
      <div class="message" id="feedback-${question.id}"></div>
    </article>
  `;
}

async function submitAnswer(questionId) {
  const checked = qs(`input[name="answer-${questionId}"]:checked`);
  const textarea = qs(`#answer-${questionId}`);
  const answer = checked ? checked.value : textarea?.value || "";
  if (!answer.trim()) return;
  try {
    const data = await api("/quiz/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: USER_ID, question_id: questionId, answer }),
    });
    qs(`#feedback-${questionId}`).textContent = `Score: ${data.score}%. ${data.feedback} Next difficulty: ${data.next.difficulty}.`;
  } catch (error) {
    qs(`#feedback-${questionId}`).textContent = error.message;
    qs(`#feedback-${questionId}`).classList.add("error");
  }
}

async function loadDashboard() {
  const data = await api(`/dashboard?user_id=${USER_ID}`);
  qs("#avgScore").textContent = `${data.average_score}%`;
  qs("#attemptCount").textContent = data.attempt_count;
  qs("#weakTopics").textContent = data.weak_topics.join(", ") || "None yet";
  qs("#topicPerformance").innerHTML =
    data.topic_performance
      .map((row) => `<div class="topic-row"><strong>${row.topic}</strong><span>${row.average}% across ${row.attempts} attempts</span></div>`)
      .join("") || '<div class="message">No topic history yet.</div>';
  qs("#trend").innerHTML =
    data.trend
      .map((row) => `<div class="bar" title="${row.topic}: ${row.score}%" style="height:${Math.max(row.score, 4)}%"></div>`)
      .join("") || '<div class="message">No attempts yet.</div>';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

qsa(".tab").forEach((tab) => tab.addEventListener("click", () => switchView(tab.dataset.view)));
qs("#uploadForm").addEventListener("submit", uploadPdf);
qs("#refreshDocs").addEventListener("click", loadDocuments);
qs("#askForm").addEventListener("submit", askQuestion);
qs("#generateQuiz").addEventListener("click", generateQuiz);

checkHealth();
loadDocuments().catch(() => {});
