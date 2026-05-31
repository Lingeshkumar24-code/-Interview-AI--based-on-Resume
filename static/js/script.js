/**
 * script.js – InterviewAI Frontend Logic
 * Handles: Upload, Interview flow, Voice input, Timer, Charts, PDF Download
 */

'use strict';

// ═══════════════════════════════════════════════
// GLOBAL NAMESPACE
// ═══════════════════════════════════════════════
const InterviewAI = (function () {

  // ─────────────────────────────────────────────
  // UTILITIES
  // ─────────────────────────────────────────────

  function $(id) { return document.getElementById(id); }
  function $$(sel) { return document.querySelectorAll(sel); }

  /** Show a toast notification */
  function toast(message, type = 'info', duration = 4000) {
    const container = $('toastContainer');
    if (!container) return;

    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${message}</span>`;
    container.appendChild(el);

    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(20px)';
      el.style.transition = 'all 0.3s ease';
      setTimeout(() => el.remove(), 300);
    }, duration);
  }

  /** Show/hide the loading overlay */
  function setLoading(visible, text = 'Processing...', subtext = '') {
    const overlay = $('loadingOverlay');
    if (!overlay) return;
    overlay.classList.toggle('visible', visible);
    if ($('loadingText')) $('loadingText').textContent = text;
    if ($('loadingSubtext') && subtext) $('loadingSubtext').textContent = subtext;
  }

  /** Animate a number counting up */
  function animateCount(el, from, to, duration = 1000) {
    if (!el) return;
    const start = performance.now();
    const update = (time) => {
      const elapsed = time - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      el.textContent = (from + (to - from) * eased).toFixed(1);
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }

  // ─────────────────────────────────────────────
  // PAGE: INDEX – RESUME UPLOAD
  // ─────────────────────────────────────────────

  function initUploadPage() {
    const zone = $('uploadZone');
    const input = $('resumeInput');
    const uploadBtn = $('uploadBtn');

    if (!zone || !input) return;

    // Click to browse
    uploadBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      input.click();
    });

    zone.addEventListener('click', () => input.click());

    // File selected via browse
    input.addEventListener('change', () => {
      if (input.files.length > 0) handleFileUpload(input.files[0]);
    });

    // Drag & Drop
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));

    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) handleFileUpload(file);
    });
  }

  function handleFileUpload(file) {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast('Please upload a PDF file only.', 'error');
      return;
    }

    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
      toast('File too large. Maximum size is 16MB.', 'error');
      return;
    }

    const zone = $('uploadZone');
    const progressContainer = $('uploadProgress');
    const progressFill = $('progressFill');
    const progressLabel = $('progressLabel');

    // Update UI
    if (zone) {
      zone.querySelector('.upload-icon').textContent = '⏳';
      zone.querySelector('.upload-title').textContent = `Uploading ${file.name}...`;
    }

    progressContainer?.classList.add('visible');
    setLoading(false); // Don't use full-screen loading for upload

    // Simulate upload progress (real upload below)
    let fakeProgress = 0;
    const progressInterval = setInterval(() => {
      fakeProgress = Math.min(fakeProgress + Math.random() * 15, 85);
      if (progressFill) progressFill.style.width = fakeProgress + '%';
      if (progressLabel) {
        const msgs = ['Reading PDF...', 'Extracting text...', 'Analyzing resume...', 'Generating questions...'];
        progressLabel.textContent = msgs[Math.floor(fakeProgress / 25)] || 'Processing...';
      }
    }, 300);

    // Build FormData and POST
    const formData = new FormData();
    formData.append('resume', file);

    setLoading(true, 'Analyzing your resume...', 'Gemini AI is reading your skills and generating personalized questions');

    fetch('/upload', {
      method: 'POST',
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      clearInterval(progressInterval);
      setLoading(false);

      if (data.error) {
        toast(data.error, 'error', 6000);
        resetUploadZone();
        progressContainer?.classList.remove('visible');
        return;
      }

      // Show 100% progress
      if (progressFill) progressFill.style.width = '100%';
      if (progressLabel) progressLabel.textContent = '✅ Ready! Redirecting to interview...';

      // Show detected skills
      if (data.skills_found && data.skills_found.length > 0) {
        showSkillsTags(data.skills_found);
      }

      toast(`Welcome ${data.candidate_name}! ${data.total_questions} questions ready (${data.difficulty} level).`, 'success', 3000);

      // Redirect to interview after short delay
      setTimeout(() => {
        window.location.href = data.redirect;
      }, 1500);
    })
    .catch(err => {
      clearInterval(progressInterval);
      setLoading(false);
      toast('Upload failed. Please check your connection and try again.', 'error');
      resetUploadZone();
      progressContainer?.classList.remove('visible');
      console.error('Upload error:', err);
    });
  }

  function showSkillsTags(skills) {
    const container = $('skillsFound');
    const tags = $('skillsTags');
    if (!container || !tags) return;

    tags.innerHTML = '';
    skills.slice(0, 12).forEach((skill, i) => {
      const tag = document.createElement('span');
      tag.className = 'skill-tag';
      tag.textContent = skill;
      tag.style.animationDelay = `${i * 0.05}s`;
      tags.appendChild(tag);
    });

    container.classList.add('visible');
  }

  function resetUploadZone() {
    const zone = $('uploadZone');
    if (zone) {
      zone.querySelector('.upload-icon').textContent = '📄';
      zone.querySelector('.upload-title').textContent = 'Drop your resume here';
    }
  }

  // ─────────────────────────────────────────────
  // PAGE: INTERVIEW
  // ─────────────────────────────────────────────

  // Interview state
  let interviewState = {
    sessionId: null,
    questions: [],
    currentIndex: 0,
    completedCount: 0,
    currentQuestionId: null,
    awaitingFollowup: false,
    followupQuestionId: null,
    timerInterval: null,
    timerSeconds: 120, // 2 minutes per question
    timerPaused: false,
    voiceRecognition: null,
    isRecording: false,
    speechSynth: window.speechSynthesis,
  };

  function initInterviewPage() {
    const sessionDataEl = $('sessionData');
    const questionsJson = $('questionsJson');

    if (!sessionDataEl || !questionsJson) return;

    interviewState.sessionId = parseInt(sessionDataEl.dataset.sessionId);
    interviewState.questions = JSON.parse(questionsJson.textContent || '[]');

    if (interviewState.questions.length === 0) {
      toast('No questions found. Please start a new interview.', 'error');
      return;
    }

    // Bind buttons
    $('submitAnswerBtn')?.addEventListener('click', submitCurrentAnswer);
    $('skipBtn')?.addEventListener('click', skipCurrentQuestion);
    $('nextQuestionBtn')?.addEventListener('click', nextQuestion);
    $('finishInterviewBtn')?.addEventListener('click', finalizeInterview);
    $('endInterviewEarlyBtn')?.addEventListener('click', () => {
      if (confirm('End interview early and generate report?')) finalizeInterview();
    });
    $('voiceBtn')?.addEventListener('click', toggleVoice);
    $('clearBtn')?.addEventListener('click', () => {
      if ($('answerTextarea')) $('answerTextarea').value = '';
    });
    $('readQuestionBtn')?.addEventListener('click', readQuestionAloud);
    $('pauseTimerBtn')?.addEventListener('click', toggleTimer);
    $('resetTimerBtn')?.addEventListener('click', resetTimer);

    // Load first question
    loadQuestion(0);
    startTimer();
  }

  function loadQuestion(index) {
    const questions = interviewState.questions;

    if (index >= questions.length) {
      // All questions answered – show finish button
      const finishBtn = $('finishInterviewBtn');
      const nextBtn = $('nextQuestionBtn');
      if (finishBtn) finishBtn.style.display = 'inline-flex';
      if (nextBtn) nextBtn.style.display = 'none';
      return;
    }

    const q = questions[index];
    interviewState.currentIndex = index;
    interviewState.currentQuestionId = q.id;
    interviewState.awaitingFollowup = false;

    // Update question display
    animateQuestionIn(q);
    updateProgress(index, questions.length);
    updateTypeBadge(q.question_type);
    resetEvaluationCard();
    resetFollowupBanner();

    // Clear previous answer
    if ($('answerTextarea')) $('answerTextarea').value = '';
    if ($('answerSection')) $('answerSection').style.display = 'block';

    // Reset timer
    resetTimer();
    startTimer();
  }

  function animateQuestionIn(q) {
    const card = $('questionCard');
    const textEl = $('questionText');
    const numEl = $('qNumLabel');
    const indexEl = $('questionIndexDisplay');

    if (!card || !textEl) return;

    // Fade out then in
    card.style.opacity = '0';
    card.style.transform = 'translateY(10px)';

    setTimeout(() => {
      if (textEl) textEl.textContent = q.question_text;
      if (numEl) numEl.textContent = interviewState.currentIndex + 1;
      if (indexEl) indexEl.textContent = interviewState.currentIndex + 1;
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 150);
  }

  function updateTypeBadge(type) {
    const badge = $('questionTypeBadge');
    if (!badge) return;
    const labels = { technical: '🔧 Technical', project: '🛠️ Project', hr: '🤝 HR', followup: '⚡ Follow-up' };
    badge.textContent = labels[type] || type;
    badge.className = `question-type-badge ${type}`;
  }

  function updateProgress(currentIndex, total) {
    // Update dot indicators
    for (let i = 0; i < total; i++) {
      const dot = $(`dot-${i}`);
      if (!dot) continue;
      if (i < currentIndex) {
        dot.className = 'q-dot done';
      } else if (i === currentIndex) {
        dot.className = 'q-dot current';
      } else {
        dot.className = 'q-dot';
      }
    }

    // Update progress bar
    const fill = $('overallProgress');
    const count = $('completedCount');
    if (fill) fill.style.width = `${(currentIndex / total * 100).toFixed(1)}%`;
    if (count) count.textContent = currentIndex;
  }

  function resetEvaluationCard() {
    const card = $('evaluationCard');
    if (card) card.classList.remove('visible');
    const nextBtn = $('nextQuestionBtn');
    const finishBtn = $('finishInterviewBtn');
    if (nextBtn) nextBtn.style.display = 'none';
    if (finishBtn) finishBtn.style.display = 'none';
  }

  function resetFollowupBanner() {
    const banner = $('followupBanner');
    if (banner) banner.classList.remove('visible');
  }

  async function submitCurrentAnswer() {
    const textarea = $('answerTextarea');
    const answer = textarea?.value.trim();

    if (!answer || answer.length < 3) {
      toast('Please type an answer before submitting.', 'warning');
      textarea?.focus();
      return;
    }

    const btn = $('submitAnswerBtn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-inline"></span> Evaluating...';
    }

    setLoading(true, 'Evaluating your answer...', 'Gemini AI is analyzing your response for accuracy and completeness');
    stopTimer();

    try {
      const response = await fetch('/api/submit-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: interviewState.sessionId,
          question_id: interviewState.currentQuestionId,
          answer: answer
        })
      });

      const data = await response.json();
      setLoading(false);

      if (data.error) {
        toast(data.error, 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = 'Submit Answer <span>→</span>'; }
        return;
      }

      // Disable submit, hide skip
      if (btn) btn.style.display = 'none';
      const skipBtn = $('skipBtn');
      if (skipBtn) skipBtn.style.display = 'none';

      // Show evaluation card
      showEvaluation(data.evaluation);

      // Show follow-up if any
      if (data.followup && data.followup.text) {
        showFollowupBanner(data.followup.text, data.followup.id);
      }

      // Increment completed
      interviewState.completedCount++;

      // Decide next button
      const isLast = interviewState.currentIndex >= interviewState.questions.length - 1 && !data.followup;
      const nextBtn = $('nextQuestionBtn');
      const finishBtn = $('finishInterviewBtn');

      if (isLast) {
        if (finishBtn) finishBtn.style.display = 'inline-flex';
      } else {
        if (nextBtn) nextBtn.style.display = 'inline-flex';
      }

      // Mark dot as done
      const dot = $(`dot-${interviewState.currentIndex}`);
      if (dot) dot.className = 'q-dot done';

    } catch (err) {
      setLoading(false);
      toast('Network error. Please try again.', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = 'Submit Answer <span>→</span>'; }
      console.error('Submit answer error:', err);
    }
  }

  function showEvaluation(evaluation) {
    const card = $('evaluationCard');
    if (!card) return;

    // Score badge
    const scoreBadge = $('evalScoreBadge');
    if (scoreBadge) {
      const score = evaluation.score;
      scoreBadge.textContent = `${score}/10`;
      scoreBadge.className = `score-badge ${score >= 7 ? 'high' : score >= 5 ? 'medium' : 'low'}`;
    }

    // Strengths
    const strengthsList = $('strengthsList');
    if (strengthsList) {
      strengthsList.innerHTML = (evaluation.strengths || []).map(s => `<li>${s}</li>`).join('');
    }

    // Missing
    const missingList = $('missingList');
    if (missingList) {
      missingList.innerHTML = (evaluation.missing || []).map(m => `<li>${m}</li>`).join('');
    }

    // Improved answer
    const improvedBox = $('improvedAnswer');
    if (improvedBox) {
      improvedBox.textContent = evaluation.improved_answer || '';
    }

    card.classList.add('visible');

    // Scroll to evaluation
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Show brief feedback toast
    if (evaluation.brief_feedback) {
      toast(evaluation.brief_feedback, evaluation.score >= 7 ? 'success' : 'info', 5000);
    }
  }

  function showFollowupBanner(text, questionId) {
    const banner = $('followupBanner');
    const textEl = $('followupText');
    if (!banner || !textEl) return;

    textEl.textContent = text;
    banner.classList.add('visible');
    interviewState.awaitingFollowup = true;

    // Add follow-up to question list for next iteration
    if (questionId) {
      interviewState.questions.push({
        id: questionId,
        question_text: text,
        question_type: 'followup',
        order_num: interviewState.questions.length + 1,
        is_followup: 1
      });

      // Update total display
      const totalEl = $('questionTotalDisplay');
      if (totalEl) totalEl.textContent = interviewState.questions.length;
    }
  }

  function nextQuestion() {
    // Reset submit button
    const submitBtn = $('submitAnswerBtn');
    if (submitBtn) {
      submitBtn.style.display = 'inline-flex';
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Submit Answer <span>→</span>';
    }

    const skipBtn = $('skipBtn');
    if (skipBtn) skipBtn.style.display = 'inline-flex';

    const nextIndex = interviewState.currentIndex + 1;
    loadQuestion(nextIndex);
  }

  async function skipCurrentQuestion() {
    // Submit a placeholder answer for skipped question
    const textarea = $('answerTextarea');
    if (textarea && !textarea.value.trim()) {
      textarea.value = 'I will skip this question.';
    }
    await submitCurrentAnswer();
  }

  async function finalizeInterview() {
    setLoading(true, 'Generating your report...', 'AI is calculating scores and writing personalized recommendations');

    try {
      const response = await fetch(`/api/finalize/${interviewState.sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();
      setLoading(false);

      if (data.error) {
        toast(data.error, 'error');
        return;
      }

      toast('Interview complete! Loading your report...', 'success');
      setTimeout(() => {
        window.location.href = data.redirect;
      }, 1000);
    } catch (err) {
      setLoading(false);
      toast('Failed to generate report. Please try again.', 'error');
      console.error('Finalize error:', err);
    }
  }

  // ─────────────────────────────────────────────
  // TIMER
  // ─────────────────────────────────────────────

  const TIMER_DURATION = 120; // 2 minutes in seconds
  const RING_CIRCUMFERENCE = 2 * Math.PI * 35; // ≈ 220

  function startTimer() {
    interviewState.timerSeconds = TIMER_DURATION;
    interviewState.timerPaused = false;
    updateTimerDisplay(TIMER_DURATION);

    clearInterval(interviewState.timerInterval);
    interviewState.timerInterval = setInterval(() => {
      if (interviewState.timerPaused) return;

      interviewState.timerSeconds--;
      updateTimerDisplay(interviewState.timerSeconds);

      if (interviewState.timerSeconds <= 0) {
        clearInterval(interviewState.timerInterval);
        toast('⏰ Time\'s up! Consider submitting your answer.', 'warning', 5000);
      }
    }, 1000);
  }

  function stopTimer() {
    clearInterval(interviewState.timerInterval);
  }

  function resetTimer() {
    stopTimer();
    interviewState.timerSeconds = TIMER_DURATION;
    updateTimerDisplay(TIMER_DURATION);
    if (!interviewState.timerPaused) startTimer();
  }

  function toggleTimer() {
    interviewState.timerPaused = !interviewState.timerPaused;
    const btn = $('pauseTimerBtn');
    if (btn) btn.textContent = interviewState.timerPaused ? '▶ Resume' : '⏸ Pause';
  }

  function updateTimerDisplay(seconds) {
    const ringFill = $('timerRingFill');
    const textEl = $('timerText');

    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const display = `${mins}:${secs.toString().padStart(2, '0')}`;

    if (textEl) textEl.textContent = display;

    // Update ring
    const ratio = Math.max(0, seconds / TIMER_DURATION);
    const offset = RING_CIRCUMFERENCE * (1 - ratio);
    if (ringFill) {
      ringFill.style.strokeDashoffset = offset;

      if (seconds <= 30) {
        ringFill.classList.add('danger');
        ringFill.classList.remove('warning');
      } else if (seconds <= 60) {
        ringFill.classList.add('warning');
        ringFill.classList.remove('danger');
      } else {
        ringFill.classList.remove('warning', 'danger');
      }
    }
  }

  // ─────────────────────────────────────────────
  // VOICE FEATURES
  // ─────────────────────────────────────────────

  function toggleVoice() {
    if (interviewState.isRecording) {
      stopVoiceRecording();
    } else {
      startVoiceRecording();
    }
  }

  function startVoiceRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      toast('Voice input not supported in this browser. Use Chrome for best results.', 'warning');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      interviewState.isRecording = true;
      const btn = $('voiceBtn');
      if (btn) btn.classList.add('recording');
      btn.title = 'Stop recording';
      btn.textContent = '⏹️';

      const statusEl = $('voiceStatus');
      if (statusEl) statusEl.style.display = 'block';
      toast('🎙️ Recording started. Speak your answer...', 'info', 2000);
    };

    recognition.onresult = (event) => {
      const textarea = $('answerTextarea');
      if (!textarea) return;

      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        textarea.value += finalTranscript;
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      if (event.error !== 'no-speech') {
        toast(`Voice error: ${event.error}`, 'error');
      }
      stopVoiceRecording();
    };

    recognition.onend = () => {
      if (interviewState.isRecording) {
        // Auto-restart if still recording
        recognition.start();
      }
    };

    interviewState.voiceRecognition = recognition;
    recognition.start();
  }

  function stopVoiceRecording() {
    interviewState.isRecording = false;

    if (interviewState.voiceRecognition) {
      interviewState.voiceRecognition.stop();
      interviewState.voiceRecognition = null;
    }

    const btn = $('voiceBtn');
    if (btn) {
      btn.classList.remove('recording');
      btn.title = 'Record voice answer';
      btn.textContent = '🎙️';
    }

    const statusEl = $('voiceStatus');
    if (statusEl) statusEl.style.display = 'none';

    toast('🛑 Recording stopped.', 'info', 2000);
  }

  function readQuestionAloud() {
    const text = $('questionText')?.textContent;
    if (!text || !window.speechSynthesis) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);

    const btn = $('readQuestionBtn');
    if (btn) {
      btn.textContent = '🔊';
      utterance.onend = () => { if (btn) btn.textContent = '🔊'; };
    }
  }

  // ─────────────────────────────────────────────
  // PAGE: RESULT – CHARTS & ANIMATIONS
  // ─────────────────────────────────────────────

  function initResultPage() {
    const reportEl = $('reportData');
    if (!reportEl) return;

    const scores = {
      overall:       parseFloat(reportEl.dataset.overall) || 0,
      technical:     parseFloat(reportEl.dataset.technical) || 0,
      project:       parseFloat(reportEl.dataset.project) || 0,
      communication: parseFloat(reportEl.dataset.communication) || 0,
      confidence:    parseFloat(reportEl.dataset.confidence) || 0,
      hr:            parseFloat(reportEl.dataset.hr) || 0,
    };

    // Animate overall score ring
    animateScoreRing(scores.overall);

    // Animate score mini-bars
    setTimeout(() => {
      $$('.score-mini-bar-fill').forEach(bar => {
        const score = parseFloat(bar.dataset.score) || 0;
        bar.style.width = `${(score / 10) * 100}%`;
      });
    }, 300);

    // Draw charts
    setTimeout(() => {
      drawRadarChart(scores);
      drawBarChart(scores);
    }, 500);
  }

  function animateScoreRing(score) {
    const fillEl = $('scoreFill');
    const numEl = $('overallScoreNum');

    if (!fillEl) return;

    const circumference = 2 * Math.PI * 52; // r=52 → ≈326.7
    const offset = circumference - (score / 10) * circumference;

    setTimeout(() => {
      fillEl.style.strokeDashoffset = offset;
    }, 300);

    if (numEl) {
      animateCount(numEl, 0, score, 1500);
    }
  }

  function drawRadarChart(scores) {
    const canvas = $('radarChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const r = Math.min(cx, cy) - 40;

    const labels = ['Technical', 'Projects', 'Communication', 'Confidence', 'HR'];
    const values = [
      scores.technical / 10,
      scores.project / 10,
      scores.communication / 10,
      scores.confidence / 10,
      scores.hr / 10
    ];

    const n = labels.length;
    const angleStep = (2 * Math.PI) / n;
    const startAngle = -Math.PI / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid rings
    for (let ring = 1; ring <= 5; ring++) {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const angle = startAngle + i * angleStep;
        const x = cx + (r * ring / 5) * Math.cos(angle);
        const y = cy + (r * ring / 5) * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.12)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw axis lines
    for (let i = 0; i < n; i++) {
      const angle = startAngle + i * angleStep;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw data polygon
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const angle = startAngle + i * angleStep;
      const x = cx + r * values[i] * Math.cos(angle);
      const y = cy + r * values[i] * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();

    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    gradient.addColorStop(0, 'rgba(124, 58, 237, 0.4)');
    gradient.addColorStop(1, 'rgba(6, 182, 212, 0.1)');
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.strokeStyle = 'rgba(124, 58, 237, 0.8)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw dots at vertices
    for (let i = 0; i < n; i++) {
      const angle = startAngle + i * angleStep;
      const x = cx + r * values[i] * Math.cos(angle);
      const y = cy + r * values[i] * Math.sin(angle);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = '#7C3AED';
      ctx.fill();
      ctx.strokeStyle = '#A78BFA';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw labels
    ctx.font = '500 11px Inter, sans-serif';
    ctx.fillStyle = '#94A3B8';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let i = 0; i < n; i++) {
      const angle = startAngle + i * angleStep;
      const lx = cx + (r + 22) * Math.cos(angle);
      const ly = cy + (r + 22) * Math.sin(angle);
      ctx.fillText(labels[i], lx, ly);
    }
  }

  function drawBarChart(scores) {
    const canvas = $('barChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const padding = { top: 20, right: 20, bottom: 40, left: 40 };
    const w = canvas.width - padding.left - padding.right;
    const h = canvas.height - padding.top - padding.bottom;

    const labels = ['Technical', 'Projects', 'Comms', 'Confidence', 'HR'];
    const values = [scores.technical, scores.project, scores.communication, scores.confidence, scores.hr];
    const colors = ['#7C3AED', '#06B6D4', '#10B981', '#F59E0B', '#EF4444'];

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(padding.left, padding.top);

    const barWidth = w / labels.length * 0.65;
    const gap = w / labels.length;

    // Y-axis gridlines & labels
    for (let i = 0; i <= 10; i += 2) {
      const y = h - (i / 10) * h;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.font = '10px Inter';
      ctx.fillStyle = '#475569';
      ctx.textAlign = 'right';
      ctx.fillText(i, -5, y + 4);
    }

    // Bars
    labels.forEach((label, i) => {
      const x = i * gap + (gap - barWidth) / 2;
      const val = values[i] || 0;
      const barH = (val / 10) * h;
      const y = h - barH;

      // Bar gradient
      const grad = ctx.createLinearGradient(x, y, x, h);
      grad.addColorStop(0, colors[i]);
      grad.addColorStop(1, colors[i] + '44');

      ctx.beginPath();
      ctx.roundRect ? ctx.roundRect(x, y, barWidth, barH, 4) :
        ctx.rect(x, y, barWidth, barH);
      ctx.fillStyle = grad;
      ctx.fill();

      // Value label on top of bar
      ctx.font = 'bold 11px Inter';
      ctx.fillStyle = '#F8FAFC';
      ctx.textAlign = 'center';
      ctx.fillText(val.toFixed(1), x + barWidth / 2, y - 6);

      // X axis label
      ctx.font = '10px Inter';
      ctx.fillStyle = '#94A3B8';
      ctx.fillText(label, x + barWidth / 2, h + 16);
    });

    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  // ─────────────────────────────────────────────
  // PAGE: HISTORY – FILTER
  // ─────────────────────────────────────────────

  function initHistoryPage() {
    // Nothing special needed on load
  }

  function filterHistory(searchTerm) {
    const difficulty = $('difficultyFilter')?.value.toLowerCase() || '';
    const status = $('statusFilter')?.value.toLowerCase() || '';
    const term = searchTerm.toLowerCase();

    const rows = $$('.history-row');
    let visibleCount = 0;

    rows.forEach(row => {
      const filename = row.dataset.filename || '';
      const diff = row.dataset.difficulty || '';
      const stat = row.dataset.status || '';

      const matchSearch = !term || filename.includes(term);
      const matchDiff = !difficulty || diff === difficulty;
      const matchStatus = !status || stat === status;

      if (matchSearch && matchDiff && matchStatus) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    const noResults = $('noResultsMsg');
    if (noResults) {
      noResults.classList.toggle('hidden', visibleCount > 0);
    }
  }

  // ─────────────────────────────────────────────
  // Q&A ACCORDION TOGGLE
  // ─────────────────────────────────────────────

  function toggleQA(id) {
    const item = $(id);
    if (!item) return;
    item.classList.toggle('open');
  }

  // ─────────────────────────────────────────────
  // PDF DOWNLOAD (Print-friendly)
  // ─────────────────────────────────────────────

  function downloadReport() {
    toast('Preparing PDF report...', 'info', 2000);
    setTimeout(() => {
      window.print();
    }, 500);
  }

  // ─────────────────────────────────────────────
  // INTERVIEW ROUNDS TAB SWITCHER
  // ─────────────────────────────────────────────

  function switchRound(panelId, tabEl) {
    // Deactivate all panels + tabs
    document.querySelectorAll('.round-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.round-tab').forEach(t => t.classList.remove('active'));

    // Activate selected
    const panel = document.getElementById(panelId);
    if (panel) panel.classList.add('active');
    if (tabEl) tabEl.classList.add('active');
  }

  // ─────────────────────────────────────────────
  // INITIALIZATION ON PAGE LOAD
  // ─────────────────────────────────────────────

  function init() {
    // Initialize upload page if upload zone exists
    if ($('uploadZone')) {
      initUploadPage();
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ─────────────────────────────────────────────
  // PUBLIC API
  // ─────────────────────────────────────────────
  return {
    initInterviewPage,
    initResultPage,
    initHistoryPage,
    toggleQA,
    downloadReport,
    filterHistory,
    switchRound,
    toast,
  };

})();
