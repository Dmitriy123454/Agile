let a, b;
let correct = 0;
let wrong = 0;
let points = 0;
let timer = 10;
let timerId = null;
let started = false; // флаг — игра началась или нет

const problemEl = document.getElementById("problem");
const answerEl = document.getElementById("answer");
const timerEl = document.getElementById("timer");
const correctEl = document.getElementById("correct");
const wrongEl = document.getElementById("wrong");
const pointsEl = document.getElementById("points");

// Генерация новой задачи
function newTask() {
  a = Math.floor(Math.random() * 9) + 1;
  b = Math.floor(Math.random() * 9) + 1;
  problemEl.textContent = `${a} × ${b} =`;
  answerEl.value = "";
  answerEl.focus();
}

// Запуск таймера
function startTimer() {
  if (timerId) return; // если уже запущен — не дублируем
  timer = 10;
  timerEl.textContent = timer;

  timerId = setInterval(() => {
    timer--;
    timerEl.textContent = timer;
    if (timer <= 0) endGame();
  }, 1000);
}

// Завершение тренировки
function endGame() {
  clearInterval(timerId);
  timerId = null;
  answerEl.disabled = true;

  const total = correct + wrong || 1;
  const avg = 10 / total; // или своя метрика среднего времени

  fetch("/result", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      correct,
      wrong,
      points,
      avg_time: avg
    })
  })
    .then((r) => r.text())
    .then((html) => {
      document.open();
      document.write(html);
      document.close();
    })
    .catch((e) => console.error(e));
}

// Проверка ответа
function checkAnswer() {
  const userAnswer = Number(answerEl.value.trim());
  if (isNaN(userAnswer) || answerEl.value === "") return;

  // если это первый ввод — запускаем таймер
  if (!started) {
    started = true;
    startTimer();
  }

  const rightAnswer = a * b;
  if (userAnswer === rightAnswer) {
    correct++;
    points += 10;
  } else {
    wrong++;
    points = Math.max(0, points - 5);
  }

  correctEl.textContent = correct;
  wrongEl.textContent = wrong;
  pointsEl.textContent = points;

  newTask();
}

// Обработка Enter
answerEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") checkAnswer();
});

// Первая задача при загрузке
newTask();
