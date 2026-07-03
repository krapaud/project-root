const AI_SERVICE_URL = "http://localhost:9000/query";

const form = document.getElementById("query-form");
const input = document.getElementById("question");
const responseBox = document.getElementById("response");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) {
    return;
  }

  responseBox.className = "loading";
  responseBox.textContent = "Thinking...";

  try {
    const res = await fetch(AI_SERVICE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      throw new Error(`Server responded with status ${res.status}`);
    }

    const data = await res.json();
    responseBox.className = "";
    responseBox.textContent = data.answer;
  } catch (err) {
    responseBox.className = "error";
    responseBox.textContent = `Something went wrong: ${err.message}. Please try again.`;
  }
});
