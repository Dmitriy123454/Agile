
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
    problemEl.textContent = `${t.a} × ${t.b} =`;
    answerEl.value = '';
    answerEl.focus();
    startTime = Date.now();
  }

  function updateSidebar(){
    pointsEl.textContent = points;
    correctEl.textContent = correct;
    wrongEl.textContent = wrong;
  }

  function tick(){
    timer--;
    timerEl.textContent = timer;
    if(timer <= 0){
      finish();
    } else {
      setTimeout(tick, 1000);
    }
  }

  function finish(){
    answerEl.disabled = true;
    const avg = answerTimes.length ? (answerTimes.reduce((a,b)=>a+b,0)/answerTimes.length) : 0;
    // POST results, then navigate to the rendered result page
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

  answerEl.addEventListener('keydown', (e)=>{
    if(e.key === 'Enter'){
      const val = Number(answerEl.value);
      const elapsed = (Date.now() - startTime)/1000;
      if(val === current.answer){
        correct++;
        points++;
        answerTimes.push(elapsed);
        problemEl.classList.add('blink-green');
      }else{
        wrong++;
        problemEl.classList.add('blink-red');
      }
      updateSidebar();
      setTimeout(()=>{
        problemEl.classList.remove('blink-green','blink-red');
        newTask();
      }, 120);
    }
  });

  // Visual feedback
  const style = document.createElement('style');
  style.textContent = `
    .blink-green{color:#16a34a}
    .blink-red{color:#ef4444}
  `;
  document.head.appendChild(style);

  // boot
  timerEl.textContent = timer;
  newTask();
  setTimeout(tick, 1000);
})();
