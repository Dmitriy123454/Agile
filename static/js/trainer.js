(function(){
  const timeLimit = 10; // seconds (for debugging per the task)
  const problemEl = document.getElementById('problem');
  const answerEl = document.getElementById('answer');
  const timerEl = document.getElementById('timer');
  const pointsEl = document.getElementById('points');
  const correctEl = document.getElementById('correct');
  const wrongEl = document.getElementById('wrong');

  let current = null;
  let correct = 0;
  let wrong = 0;
  let points = 0;
  let startTime = Date.now();
  let answerTimes = [];
  let timer = timeLimit;

  async function newTask() {
    const r = await fetch('/api/task');
    const t = await r.json();
    current = t;
    if (problemEl) {
      problemEl.textContent = `${t.a} × ${t.b} =`;
    }
    if (answerEl) {
      answerEl.value = '';
      answerEl.disabled = false;
      answerEl.focus();
    }
    startTime = Date.now();
  }

  function updateSidebar(){
    if (pointsEl) pointsEl.textContent = points;
    if (correctEl) correctEl.textContent = correct;
    if (wrongEl) wrongEl.textContent = wrong;
  }

  function tick(){
    timer--;
    if (timerEl) timerEl.textContent = timer;
    if(timer <= 0){
      finish();
    } else {
      setTimeout(tick, 1000);
    }
  }

  function finish(){
    if (answerEl) answerEl.disabled = true;
    const avg = answerTimes.length
      ? (answerTimes.reduce((a,b)=>a+b,0)/answerTimes.length)
      : 0;

    // POST results, затем сервер вернёт готовую HTML-страницу результата
    fetch('/result', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({points, correct, wrong, avg_time: avg})
    }).then(r=>r.text()).then(html=>{
      document.open();
      document.write(html);
      document.close();
    });
  }

  if (answerEl) {
    answerEl.addEventListener('keydown', (e)=>{
      if(e.key === 'Enter'){
        const val = Number(answerEl.value);
        const elapsed = (Date.now() - startTime)/1000;

        if(val === (current ? current.answer : NaN)){
          correct++;
          points++;
          answerTimes.push(elapsed);
          if (problemEl) problemEl.classList.add('blink-green');
        } else {
          wrong++;
          if (problemEl) problemEl.classList.add('blink-red');
        }

        updateSidebar();

        setTimeout(()=>{
          if (problemEl) problemEl.classList.remove('blink-green', 'blink-red');
          newTask();
        }, 120);
      }
    });
  }

  // Visual feedback
  const style = document.createElement('style');
  style.textContent = `
    .blink-green{color:#16a34a}
    .blink-red{color:#ef4444}
  `;
  document.head.appendChild(style);

  // --- График 10 последних тренировок ---
  function renderProgressChart() {
    const stats = window.USER_STATS || {};
    const attempts = stats.last_attempts || [];
    if (!attempts.length) return;

    const canvas = document.getElementById('progressChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const labels = attempts.map((a, idx) => a.label || `#${idx + 1}`);
    const dataPoints = attempts.map(a => a.points);

    new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Очки за тренировку',
          data: dataPoints,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
            title: { display: true, text: 'Очки' }
          },
          x: {
            title: { display: true, text: 'Последние попытки' }
          }
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                const i = ctx.dataIndex;
                const a = attempts[i];
                return `Очки: ${a.points}, верно: ${a.correct}, ошибок: ${a.wrong}, ${a.percent}%`;
              }
            }
          }
        }
      }
    });
  }

  // boot
  if (timerEl) timerEl.textContent = timer;
  if (problemEl && answerEl) {
    newTask();
    setTimeout(tick, 1000);
  }
  renderProgressChart();
})();
