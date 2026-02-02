(() => {
  const chatPanel = document.getElementById('chatPanel');
  const micBtn = document.getElementById('micBtn');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const textForm = document.getElementById('textForm');
  const textInput = document.getElementById('textInput');
  const settings = document.getElementById('settings');
  const openSettings = document.getElementById('openSettings');
  const closeSettings = document.getElementById('closeSettings');
  const themeToggle = document.getElementById('themeToggle');
  const themeSelect = document.getElementById('themeSelect');
  const voiceRate = document.getElementById('voiceRate');
  const backendUrl = document.getElementById('backendUrl');
  const saveSettings = document.getElementById('saveSettings');
  const waveCanvas = document.getElementById('waveform');
  const ctx = waveCanvas.getContext('2d');

  const store = {
    theme: localStorage.getItem('luna_theme') || 'system',
    backend: localStorage.getItem('luna_backend') || 'http://localhost:8000',
    rate: parseInt(localStorage.getItem('luna_rate') || '180', 10),
  };

  function setTheme(mode) {
    if (mode === 'system') {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', mode);
    }
  }

  function setStatus(mode) {
    statusDot.className = 'dot ' + mode;
    const label = { idle: 'Idle', listening: 'Listening', processing: 'Processing', speaking: 'Speaking' }[mode] || 'Idle';
    statusText.textContent = label;
  }

  function addMsg(role, text) {
    const wrap = document.createElement('div');
    wrap.className = 'msg ' + (role === 'user' ? 'user' : 'ai');
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    wrap.appendChild(bubble);
    chatPanel.appendChild(wrap);
    chatPanel.scrollTop = chatPanel.scrollHeight;
  }

  // Simple waveform animation to indicate capture or playback
  let raf;
  function drawWave(active) {
    cancelAnimationFrame(raf);
    ctx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);
    if (!active) return;
    const w = waveCanvas.width;
    const h = waveCanvas.height;
    let t = 0;
    function loop() {
      ctx.clearRect(0, 0, w, h);
      ctx.beginPath();
      for (let x = 0; x < w; x++) {
        const y = h / 2 + Math.sin((x + t) / 10) * (h / 4);
        ctx.lineTo(x, y);
      }
      ctx.strokeStyle = '#60a5fa';
      ctx.lineWidth = 2;
      ctx.stroke();
      t += 2;
      raf = requestAnimationFrame(loop);
    }
    loop();
  }

  // --- Web Speech API (Browser ASR) ---
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let isListening = false;

  function initASR() {
    if (!SpeechRecognition) {
      setStatus('idle');
      addMsg('ai', 'This browser does not support in-browser speech recognition.');
      return;
    }
    recognition = new SpeechRecognition();
    recognition.lang = navigator.language || 'en-US';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      setStatus('listening');
      drawWave(true);
      isListening = true;
    };
    recognition.onend = () => {
      drawWave(false);
      setStatus('processing');
      isListening = false;
    };
    recognition.onerror = (e) => {
      setStatus('idle');
      drawWave(false);
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        addMsg('ai', 'Microphone permission denied. Please allow mic access in your browser.');
      } else if (e.error !== 'no-speech') {
        addMsg('ai', 'Speech recognition error: ' + e.error);
      }
    };
    recognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      // Only submit when final
      const isFinal = event.results[event.results.length - 1].isFinal;
      if (isFinal && transcript.trim()) {
        handleUserInput(transcript.trim());
      }
    };
  }

  function startListening() {
    if (!recognition) return;
    try {
      recognition.start();
    } catch (e) {
      // Ignore start() errors if already started
    }
  }

  function stopListening() {
    if (!recognition) return;
    try {
      recognition.stop();
    } catch (e) {}
  }

  async function callBackend(text) {
    // Placeholder: POST to your Python backend. Adjust endpoint names as needed.
    // Expected API: { text: string } -> { reply: string }
    try {
      const res = await fetch(store.backend + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, rate: store.rate })
      });
      if (!res.ok) throw new Error('Bad response');
      return await res.json();
    } catch (e) {
      return { reply: 'Sorry, the backend is unavailable right now.' };
    }
  }

  async function handleUserInput(text) {
    if (!text.trim()) return;
    addMsg('user', text);
    setStatus('processing');
    drawWave(false);
    const { reply } = await callBackend(text);
    addMsg('ai', reply);
    setStatus('speaking');
    drawWave(true);
    // optional: trigger TTS playback via backend
    try { await fetch(store.backend + '/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: reply, rate: store.rate }) }); } catch(e) {}
    setTimeout(() => { setStatus('idle'); drawWave(false); }, 800);
  }

  // Events
  textForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = textInput.value;
    textInput.value = '';
    handleUserInput(text);
  });

  // Press-and-hold to talk (mouse)
  micBtn.addEventListener('mousedown', () => {
    if (!isListening) startListening();
  });
  micBtn.addEventListener('mouseup', () => {
    if (isListening) stopListening();
  });
  // Press-and-hold to talk (touch)
  micBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
    if (!isListening) startListening();
  }, { passive: false });
  micBtn.addEventListener('touchend', (e) => {
    e.preventDefault();
    if (isListening) stopListening();
  }, { passive: false });

  openSettings.addEventListener('click', () => settings.setAttribute('aria-hidden', 'false'));
  closeSettings.addEventListener('click', () => settings.setAttribute('aria-hidden', 'true'));

  themeToggle.addEventListener('click', () => {
    const next = (document.documentElement.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('luna_theme', next);
    themeSelect.value = next;
  });

  saveSettings.addEventListener('click', () => {
    store.theme = themeSelect.value;
    store.backend = backendUrl.value || store.backend;
    store.rate = parseInt(voiceRate.value || store.rate, 10);
    localStorage.setItem('luna_theme', store.theme);
    localStorage.setItem('luna_backend', store.backend);
    localStorage.setItem('luna_rate', String(store.rate));
    setTheme(store.theme);
    settings.setAttribute('aria-hidden', 'true');
  });

  // Init
  themeSelect.value = store.theme;
  backendUrl.value = store.backend;
  voiceRate.value = String(store.rate);
  setTheme(store.theme);
  setStatus('idle');
  initASR();
})();


