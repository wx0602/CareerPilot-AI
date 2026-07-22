<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import { api, getSession, setSession } from '../api/client';
import interviewerImage from '../assets/ai-interviewer-lin.png';
import { createNonverbalAnalyzer } from '../services/nonverbalAnalyzer';

const router = useRouter();
const stageRef = ref(null);
const videoRef = ref(null);
const session = ref(getSession());
const messages = ref([]);
const currentQuestion = ref(null);
const answer = ref('');
const loading = ref(false);
const started = ref(false);
const speaking = ref(false);
const listening = ref(false);
const error = ref('');
const answeredCount = ref(0);
const latestScore = ref(null);
const voiceEnabled = ref(true);
const speechSupported = ref(false);
const recognitionSupported = ref(false);
const voices = ref([]);
const selectedVoice = ref('');
const speechRate = ref(1);
const simulationTurn = ref(null);
const simulationStatus = ref('active');
const stressLevel = ref('medium');
const cameraActive = ref(false);
const cameraReady = ref(false);
const cameraError = ref('');
const cameraDevices = ref([]);
const selectedCamera = ref('');
const cameraResolution = ref('');
const nonverbalStatus = ref('idle');
const currentQuestionAnalysisStarted = ref(false);
const currentQuestionId = ref(null);
const pendingAnalysisStart = ref(false);
let recognition = null;
let cameraStream = null;
let streamVersion = 0;
let questionPresentedAt = null;
let pendingAnswerStartedAt = null;
let pendingInputMode = 'text';
let nonverbalFailureReason = null;

const nonverbalAnalyzer = createNonverbalAnalyzer({
  onStateChange(state) {
    nonverbalStatus.value = state;
  }
});

const STREAM_INTERVAL = 32;

function streamDelay(character) {
  if (/[。！？!?]/.test(character)) return 140;
  if (/[，、；：,;:]/.test(character)) return 70;
  return STREAM_INTERVAL;
}

const isSimulation = computed(() =>
  ['group_interview', 'stress_interview'].includes(session.value?.mode)
);
const isGroupInterview = computed(() => session.value?.mode === 'group_interview');
const isStressInterview = computed(() => session.value?.mode === 'stress_interview');
const nonverbalEnabled = computed(() => session.value?.mode === 'job');
const nonverbalStatusText = computed(() => ({
  idle: '开启摄像头后可进行本地动作分析',
  initializing: '动作分析正在初始化',
  available: currentQuestionAnalysisStarted.value ? '正在本地分析动作与姿态' : '动作分析可用',
  unavailable: '动作分析不可用，面试可继续',
  destroyed: '动作分析已结束'
}[nonverbalStatus.value] || '动作分析不可用'));

const stageLabels = {
  case_intro: '案例介绍',
  individual_statement: '个人陈述',
  free_discussion: '自由讨论',
  disagreement_resolution: '分歧处理',
  consensus: '形成共识',
  summary: '总结',
  opening: '开场',
  probing: '连续追问',
  paused: '已暂停',
  closing: '结束',
  scoring: '评分'
};

const statusText = computed(() => {
  if (listening.value) return '正在聆听';
  if (speaking.value) return '正在提问';
  if (loading.value) return '正在思考';
  if (started.value) return '等待回答';
  return '准备就绪';
});

const interviewTitle = computed(
  () => isGroupInterview.value
    ? '无领导小组讨论'
    : isStressInterview.value
      ? '压力面试'
      : session.value?.learning_module_title || session.value?.position || '职业能力面试'
);

const currentPrompt = computed(() => {
  if (isSimulation.value) {
    return messages.value.at(-1)?.text;
  }
  return currentQuestion.value?.question;
});

function loadVoices() {
  if (!window.speechSynthesis) return;
  const available = window.speechSynthesis.getVoices();
  voices.value = available.filter((voice) => voice.lang.toLowerCase().startsWith('zh'));
  if (!voices.value.length) voices.value = available;
  if (!selectedVoice.value && voices.value.length) {
    selectedVoice.value = voices.value[0].name;
  }
}

function setupRecognition() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognitionSupported.value = Boolean(Recognition);
  if (!Recognition) return;
  recognition = new Recognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.onstart = () => {
    listening.value = true;
    requestQuestionAnalysisStart('voice');
  };
  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join('');
    if (transcript.trim()) requestQuestionAnalysisStart('voice');
    answer.value = transcript;
  };
  recognition.onend = () => {
    listening.value = false;
  };
  recognition.onerror = (event) => {
    listening.value = false;
    if (event.error !== 'no-speech') error.value = '语音输入未成功，请检查麦克风权限后重试。';
  };
}

onMounted(() => {
  speechSupported.value = 'speechSynthesis' in window;
  if (speechSupported.value) {
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
  }
  setupRecognition();
});

onBeforeUnmount(() => {
  window.speechSynthesis?.cancel();
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = null;
  recognition?.abort();
  nonverbalAnalyzer.destroy();
  cameraStream?.getTracks().forEach((track) => track.stop());
});

watch(answer, (value, previousValue) => {
  if (!nonverbalEnabled.value) return;
  if (!String(previousValue || '').trim() && String(value || '').trim()) {
    requestQuestionAnalysisStart('text');
  }
});

function prepareQuestionAnalysis(question) {
  if (!nonverbalEnabled.value) return;
  nonverbalAnalyzer.pause();
  currentQuestionId.value = question?.question_id || null;
  currentQuestionAnalysisStarted.value = false;
  pendingAnalysisStart.value = false;
  questionPresentedAt = null;
  pendingAnswerStartedAt = null;
  pendingInputMode = 'text';
}

function requestQuestionAnalysisStart(inputMode = 'text') {
  if (!nonverbalEnabled.value || !currentQuestionId.value) return;
  if (inputMode === 'voice') {
    pendingInputMode = 'voice';
    nonverbalAnalyzer.markVoiceInput();
  }
  if (currentQuestionAnalysisStarted.value) return;
  if (pendingAnswerStartedAt === null) pendingAnswerStartedAt = Date.now();
  if (
    speaking.value
    || questionPresentedAt === null
    || !cameraReady.value
    || nonverbalAnalyzer.getState() !== 'available'
  ) {
    pendingAnalysisStart.value = true;
    return;
  }
  const didStart = nonverbalAnalyzer.startQuestion(currentQuestionId.value, {
    inputMode: pendingInputMode,
    presentedAt: questionPresentedAt,
    answerStartedAt: pendingAnswerStartedAt
  });
  if (didStart) {
    currentQuestionAnalysisStarted.value = true;
    pendingAnalysisStart.value = false;
  }
}

function markQuestionReadingFinished() {
  if (!nonverbalEnabled.value || !currentQuestionId.value) return;
  if (questionPresentedAt === null) questionPresentedAt = Date.now();
  if (currentQuestionAnalysisStarted.value) {
    nonverbalAnalyzer.startQuestion(currentQuestionId.value, { inputMode: pendingInputMode });
  } else if (pendingAnalysisStart.value) {
    requestQuestionAnalysisStart(pendingInputMode);
  }
}

function finishCurrentQuestionAnalysis() {
  if (!nonverbalEnabled.value || !currentQuestionId.value) return;
  if (currentQuestionAnalysisStarted.value) {
    nonverbalAnalyzer.finishQuestion({
      questionId: currentQuestionId.value,
      submittedAt: Date.now()
    });
  }
  currentQuestionAnalysisStarted.value = false;
  pendingAnalysisStart.value = false;
  pendingAnswerStartedAt = null;
}

async function initializeNonverbalAnalysis() {
  if (!nonverbalEnabled.value || !cameraReady.value || !videoRef.value) return;
  const state = await nonverbalAnalyzer.initialize(videoRef.value);
  if (state === 'available') {
    nonverbalFailureReason = null;
    if (currentQuestionAnalysisStarted.value) {
      nonverbalAnalyzer.startQuestion(currentQuestionId.value, { inputMode: pendingInputMode });
    } else if (pendingAnalysisStart.value) {
      requestQuestionAnalysisStart(pendingInputMode);
    }
  } else if (state === 'unavailable') {
    nonverbalFailureReason = 'model_load_failed';
  }
}

async function startCamera() {
  nonverbalAnalyzer.pause();
  cameraError.value = '';
  cameraReady.value = false;
  cameraResolution.value = '';
  if (!window.isSecureContext) {
    cameraError.value = '摄像头需要 HTTPS，或使用 localhost / 127.0.0.1 访问。';
    if (nonverbalEnabled.value) nonverbalFailureReason = 'camera_disabled';
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = '当前浏览器不支持摄像头访问。';
    if (nonverbalEnabled.value) nonverbalFailureReason = 'camera_disabled';
    return;
  }
  try {
    cameraStream?.getTracks().forEach((track) => track.stop());
    const videoConstraints = selectedCamera.value
      ? { deviceId: { exact: selectedCamera.value }, width: { ideal: 1280 }, height: { ideal: 720 } }
      : { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } };
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: videoConstraints,
      audio: false
    });
    const track = cameraStream.getVideoTracks()[0];
    if (!track) throw new Error('没有获取到视频轨道');
    const settings = track.getSettings();
    selectedCamera.value = settings.deviceId || selectedCamera.value;
    cameraResolution.value = settings.width && settings.height ? `${settings.width} × ${settings.height}` : '';
    track.onended = () => {
      nonverbalAnalyzer.pause();
      cameraActive.value = false;
      cameraReady.value = false;
      if (nonverbalEnabled.value) nonverbalFailureReason = 'camera_disabled';
      cameraError.value = '摄像头连接已中断，请重新开启。';
    };
    track.onmute = () => {
      nonverbalAnalyzer.pause();
      cameraReady.value = false;
      cameraError.value = '摄像头暂时没有输出画面，请检查是否被其他程序占用或物理遮挡。';
    };
    track.onunmute = () => {
      cameraError.value = '';
      cameraReady.value = true;
      if (currentQuestionAnalysisStarted.value) {
        nonverbalAnalyzer.startQuestion(currentQuestionId.value, { inputMode: pendingInputMode });
      } else if (pendingAnalysisStart.value) {
        requestQuestionAnalysisStart(pendingInputMode);
      }
    };

    cameraActive.value = true;
    await nextTick();
    const video = videoRef.value;
    if (!video) throw new Error('视频预览组件尚未准备好');
    video.srcObject = cameraStream;
    video.muted = true;
    await waitForVideoMetadata(video);
    await video.play();
    cameraReady.value = true;
    cameraDevices.value = (await navigator.mediaDevices.enumerateDevices())
      .filter((device) => device.kind === 'videoinput');
    await initializeNonverbalAnalysis();
  } catch (err) {
    cameraStream?.getTracks().forEach((track) => track.stop());
    cameraStream = null;
    cameraActive.value = false;
    cameraReady.value = false;
    nonverbalAnalyzer.pause();
    if (nonverbalEnabled.value) {
      nonverbalFailureReason = err?.name === 'NotAllowedError' ? 'camera_denied' : 'camera_disabled';
    }
    cameraError.value = err?.name === 'NotAllowedError'
      ? '摄像头权限被拒绝，请在浏览器地址栏中允许摄像头后重试。'
      : err?.name === 'NotFoundError'
        ? '没有检测到可用摄像头。'
        : `摄像头启动失败：${err?.message || '请检查设备是否被其他程序占用'}`;
  }
}

function waitForVideoMetadata(video) {
  if (video.readyState >= 1 && video.videoWidth > 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error('摄像头已连接，但浏览器没有收到视频画面'));
    }, 8000);
    const ready = () => {
      if (!video.videoWidth) return;
      cleanup();
      resolve();
    };
    const cleanup = () => {
      window.clearTimeout(timeout);
      video.removeEventListener('loadedmetadata', ready);
      video.removeEventListener('loadeddata', ready);
    };
    video.addEventListener('loadedmetadata', ready);
    video.addEventListener('loadeddata', ready);
  });
}

function markCameraReady() {
  cameraReady.value = true;
  cameraError.value = '';
  const video = videoRef.value;
  if (video?.videoWidth && video?.videoHeight) {
    cameraResolution.value = `${video.videoWidth} × ${video.videoHeight}`;
  }
}

function stopCamera() {
  nonverbalAnalyzer.pause();
  cameraStream?.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  if (videoRef.value) videoRef.value.srcObject = null;
  cameraActive.value = false;
  cameraReady.value = false;
  cameraResolution.value = '';
  if (nonverbalEnabled.value) nonverbalFailureReason = 'camera_disabled';
}

async function ensureSession() {
  if (session.value) return session.value;
  const created = await api.createSession({
    mode: 'job',
    position: '目标岗位',
    company: null
  });
  setSession(created);
  session.value = created;
  return created;
}

function addMessage(role, text, meta = null, displayName = null) {
  messages.value.push({ role, text, meta, displayName, id: `${Date.now()}-${messages.value.length}` });
}

async function streamMessage(role, content, meta = null, displayName = null) {
  messages.value.push({
    role,
    text: content || '',
    meta,
    displayName,
    streaming: false,
    id: `${Date.now()}-${messages.value.length}`
  });
}

async function addSimulationMessages(items) {
  const spoken = [...(items || [])].reverse().find((item) => item.speaker === 'interviewer');
  if (spoken) speak(spoken.content);
  for (const item of items || []) {
    await streamMessage(
      item.speaker,
      item.content,
      item.reply_to ? '回应其他候选人' : stageLabels[simulationTurn.value?.stage],
      item.display_name
    );
  }
}

function speak(text) {
  if (!voiceEnabled.value || !speechSupported.value || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  utterance.rate = Number(speechRate.value);
  utterance.voice = voices.value.find((voice) => voice.name === selectedVoice.value) || null;
  utterance.onstart = () => {
    speaking.value = true;
    if (nonverbalEnabled.value) nonverbalAnalyzer.pause();
  };
  utterance.onend = utterance.onerror = () => {
    speaking.value = false;
    markQuestionReadingFinished();
  };
  window.speechSynthesis.speak(utterance);
}

async function startInterview() {
  if (loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    const currentSession = await ensureSession();
    if (['group_interview', 'stress_interview'].includes(currentSession.mode)) {
      const data = await api.startSimulation({
        session_id: currentSession.session_id,
        mode: currentSession.mode,
        stress_level: currentSession.mode === 'stress_interview' ? stressLevel.value : null
      });
      simulationTurn.value = data;
      simulationStatus.value = data.status;
      if (data.stress_level) stressLevel.value = data.stress_level;
      started.value = true;
      messages.value = [];
      await addSimulationMessages(data.messages);
      return;
    }
    const data = await api.interviewMessage({ session_id: currentSession.session_id });
    currentQuestion.value = data.next_question;
    prepareQuestionAnalysis(data.next_question);
    started.value = true;
    messages.value = [];
    speak(data.next_question.question);
    await streamMessage('ai', data.next_question.question, data.is_followup ? '追问' : '面试问题');
    if (!speaking.value) markQuestionReadingFinished();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function submitAnswer() {
  const content = answer.value.trim();
  if (
    !content ||
    loading.value ||
    (isSimulation.value && simulationStatus.value === 'completed') ||
    (!isSimulation.value && !currentQuestion.value)
  ) return;
  finishCurrentQuestionAnalysis();
  window.speechSynthesis?.cancel();
  addMessage('user', content);
  answer.value = '';
  loading.value = true;
  error.value = '';
  try {
    if (isSimulation.value) {
      const data = await api.handleSimulationMessage({
        session_id: session.value.session_id,
        turn_id: simulationTurn.value.turn_id,
        message: content
      });
      simulationTurn.value = data;
      simulationStatus.value = data.status;
      if (data.stress_level) stressLevel.value = data.stress_level;
      answeredCount.value += 1;
      await addSimulationMessages(data.messages);
      return;
    }
    const data = await api.interviewMessage({
      session_id: session.value.session_id,
      question_id: currentQuestion.value.question_id,
      answer: content
    });
    answeredCount.value += 1;
    if (data.evaluation) {
      latestScore.value = data.evaluation.score;
      const strengths = data.evaluation.strengths?.join('、') || '回答切题';
      const weaknesses = data.evaluation.weaknesses?.join('、') || '暂无明显问题';
      await streamMessage(
        'feedback',
        `本轮 ${data.evaluation.score} 分。亮点：${strengths}。建议改进：${weaknesses}。`,
        '即时反馈'
      );
    }
    currentQuestion.value = data.next_question;
    prepareQuestionAnalysis(data.next_question);
    speak(data.next_question.question);
    await streamMessage('ai', data.next_question.question, data.is_followup ? '针对性追问' : '下一题');
    if (!speaking.value) markQuestionReadingFinished();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function toggleListening() {
  if (!recognitionSupported.value) {
    error.value = '当前浏览器不支持语音识别，请使用文字输入或更换 Chrome / Edge。';
    return;
  }
  error.value = '';
  if (listening.value) {
    recognition.stop();
    listening.value = false;
    return;
  }
  if (speaking.value) {
    window.speechSynthesis?.cancel();
    speaking.value = false;
    markQuestionReadingFinished();
  }
  recognition.start();
  listening.value = true;
}

function toggleVoice() {
  voiceEnabled.value = !voiceEnabled.value;
  if (!voiceEnabled.value) {
    window.speechSynthesis?.cancel();
    speaking.value = false;
    markQuestionReadingFinished();
  } else if (currentPrompt.value) {
    speak(currentPrompt.value);
  }
}

function replayQuestion() {
  if (currentPrompt.value) speak(currentPrompt.value);
}

async function toggleFullscreen() {
  if (!document.fullscreenElement) await stageRef.value?.requestFullscreen();
  else await document.exitFullscreen();
}

async function finishInterview() {
  if (!session.value || !answeredCount.value || loading.value) {
    if (!answeredCount.value) error.value = '至少完成一轮回答后才能生成报告。';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    if (isSimulation.value) {
      await api.finishSimulation({ session_id: session.value.session_id });
      await api.generateSimulationReport({ session_id: session.value.session_id });
      await router.push('/report');
      return;
    }
    if (nonverbalEnabled.value) nonverbalAnalyzer.pause();
    const nonverbalScore = nonverbalEnabled.value
      ? nonverbalAnalyzer.generateFinalResult({
        fallbackReason: nonverbalFailureReason || (!cameraActive.value ? 'camera_disabled' : null)
      })
      : null;
    await api.generateReport({
      session_id: session.value.session_id,
      ...(nonverbalScore ? { nonverbal_score: nonverbalScore } : {})
    });
    router.push('/report');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <LayoutShell>
    <section class="avatar-page">
      <div ref="stageRef" class="avatar-stage-full" :class="{ speaking, listening }">
        <img :src="interviewerImage" alt="AI 面试官林悦" class="avatar-portrait" />
        <div class="avatar-stage-shade"></div>

        <header class="avatar-stage-header">
          <div class="avatar-identity">
            <span class="avatar-online-dot"></span>
            <div><strong>{{ isGroupInterview ? '群面主持人' : isStressInterview ? '压力面试官' : '林悦' }}</strong><small>CareerPilot AI 面试官</small></div>
          </div>
          <span class="avatar-status"><i></i>{{ statusText }}</span>
        </header>

        <div v-if="speaking || listening" class="voice-orbit" aria-hidden="true">
          <i v-for="n in 20" :key="n" :style="{ '--i': n }"></i>
        </div>

        <div class="avatar-caption">
          <span>{{ started ? interviewTitle : 'AI 实景模拟面试' }}</span>
          <p>
            {{ currentPrompt || '我会根据你的目标岗位进行提问、追问与即时评分。准备好后，我们正式开始。' }}
          </p>
        </div>

        <div v-if="!started" class="avatar-start-card">
          <span>READY</span>
          <h1>{{ interviewTitle }}</h1>
          <p>准备好后开始面试，问题会由左侧数字人朗读。</p>
          <label v-if="isStressInterview">
            初始压力
            <select v-model="stressLevel">
              <option value="light">轻度</option>
              <option value="medium">中度</option>
              <option value="high">高度</option>
            </select>
          </label>
          <button class="start-interview-button" :disabled="loading" @click="startInterview">
            {{ loading ? '正在连接面试官…' : '开始面试' }}
          </button>
        </div>

        <div class="avatar-controls">
          <button :class="{ active: listening }" :title="listening ? '停止录音' : '语音回答'" @click="toggleListening">{{ listening ? '■' : '●' }}</button>
          <button :class="{ muted: !voiceEnabled }" :title="voiceEnabled ? '关闭声音' : '打开声音'" @click="toggleVoice">{{ voiceEnabled ? '◖))' : '◖×' }}</button>
          <button title="重播问题" :disabled="!currentPrompt" @click="replayQuestion">↻</button>
          <button title="全屏显示" @click="toggleFullscreen">⛶</button>
        </div>
      </div>

      <aside class="human-panel">
        <section class="human-camera" :class="{ active: cameraActive }">
          <video
            v-show="cameraActive"
            ref="videoRef"
            autoplay
            playsinline
            muted
            @playing="markCameraReady"
            @loadeddata="markCameraReady"
          ></video>

          <header class="human-stage-header">
            <div class="human-identity">
              <span class="camera-live-dot" :class="{ ready: cameraReady }"></span>
              <div><strong>我的画面</strong><small>本地摄像头预览</small></div>
            </div>
            <div class="interview-metrics">
              <span>已答 <b>{{ answeredCount }}</b></span>
              <span v-if="latestScore !== null">本轮 <b>{{ latestScore }}</b></span>
              <span v-if="isStressInterview">压力 <b>{{ { light: '轻', medium: '中', high: '高' }[stressLevel] }}</b></span>
            </div>
          </header>

          <div v-if="!cameraActive" class="camera-start-state">
            <span>LIVE CAMERA</span>
            <b>开启真人摄像头</b>
            <p>{{ cameraError || '画面仅在当前浏览器中预览，不会自动上传或保存。' }}</p>
            <button @click="startCamera">允许并开启摄像头</button>
          </div>
          <div v-else class="camera-overlay">
            <span><i :class="{ ready: cameraReady }"></i>{{ cameraReady ? `真人摄像头 ${cameraResolution}` : '正在获取画面…' }}</span>
            <div>
              <select v-if="cameraDevices.length" v-model="selectedCamera" aria-label="选择摄像头" @change="startCamera">
                <option v-for="(device, index) in cameraDevices" :key="device.deviceId" :value="device.deviceId">{{ device.label || `摄像头 ${index + 1}` }}</option>
              </select>
              <button @click="startCamera">重新连接</button>
              <button @click="stopCamera">关闭</button>
            </div>
          </div>
          <small v-if="nonverbalEnabled" class="nonverbal-status" :class="nonverbalStatus">
            {{ nonverbalStatusText }}
          </small>
          <p v-if="cameraActive && cameraError" class="camera-live-error">{{ cameraError }}</p>

          <form v-if="started" class="interview-dock" @submit.prevent="submitAnswer">
            <div class="dock-status">
              <span>{{ loading ? '正在分析回答…' : simulationStatus === 'completed' ? '面试已结束' : '请回答当前问题' }}</span>
              <small v-if="simulationTurn">{{ stageLabels[simulationTurn.stage] }}</small>
            </div>
            <textarea
              v-model="answer"
              :disabled="loading || simulationStatus === 'completed'"
              :placeholder="simulationStatus === 'completed' ? '面试已停止，请生成报告' : '输入回答，或点击麦克风使用语音输入…'"
              @keydown.enter.exact.prevent="submitAnswer"
            ></textarea>
            <div class="dock-actions">
              <button type="button" class="voice-input-button" :class="{ recording: listening }" @click="toggleListening">
                {{ listening ? '停止聆听' : '语音输入' }}
              </button>
              <span>{{ answer.length }}/10000</span>
              <button type="button" class="finish-avatar-button" :disabled="loading || !answeredCount" @click="finishInterview">结束并生成报告</button>
              <button class="send-answer-button" type="submit" :disabled="!answer.trim() || loading || simulationStatus === 'completed'">发送回答 ↑</button>
            </div>
          </form>
          <p v-if="error" class="avatar-error">{{ error }}</p>
        </section>
      </aside>
    </section>
  </LayoutShell>
</template>

<style scoped>
.avatar-page {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  height: 100vh;
  gap: 14px;
  overflow: hidden;
  padding: 16px;
  background: #e9eef5;
}

.avatar-stage-full,
.human-panel {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border-radius: 22px;
  background: #111c2c;
  box-shadow: 0 18px 48px rgba(24, 42, 67, .16);
  isolation: isolate;
}

.avatar-portrait {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 28%;
  transition: transform 1.2s cubic-bezier(.2,.75,.2,1), filter .5s ease;
}

.speaking .avatar-portrait {
  transform: scale(1.018);
  filter: saturate(1.04) brightness(1.02);
}

.avatar-stage-shade {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(7, 15, 29, .46) 0%, transparent 26%),
    linear-gradient(0deg, rgba(7, 15, 29, .88) 0%, rgba(7, 15, 29, .08) 48%);
  z-index: 1;
}

.avatar-stage-header {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 26px 28px;
  color: #fff;
}

.avatar-identity { display: flex; align-items: center; gap: 11px; }
.avatar-identity > div { display: grid; gap: 3px; }
.avatar-identity strong { font-size: 14px; letter-spacing: .5px; }
.avatar-identity small { color: rgba(255,255,255,.63); font-size: 10px; letter-spacing: .6px; }
.avatar-online-dot {
  width: 9px;
  height: 9px;
  border: 2px solid rgba(255,255,255,.65);
  border-radius: 50%;
  background: #43d79a;
  box-shadow: 0 0 0 5px rgba(67,215,154,.14);
}

.avatar-status {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 99px;
  padding: 7px 11px;
  background: rgba(9,21,40,.28);
  backdrop-filter: blur(12px);
  font-size: 10px;
}
.avatar-status i { width: 5px; height: 5px; border-radius: 50%; background: #7de6bb; }

.voice-orbit {
  position: absolute;
  left: 50%;
  top: 42%;
  z-index: 3;
  display: flex;
  height: 42px;
  align-items: center;
  gap: 3px;
  transform: translate(-50%, -50%);
  opacity: .78;
}
.voice-orbit i {
  width: 2px;
  height: calc(5px + (var(--i) % 6) * 3px);
  border-radius: 9px;
  background: rgba(255,255,255,.9);
  animation: avatar-wave .9s ease-in-out infinite alternate;
  animation-delay: calc(var(--i) * -45ms);
}
@keyframes avatar-wave { to { transform: scaleY(2.1); opacity: .45; } }

.avatar-caption {
  position: absolute;
  right: 38px;
  bottom: 92px;
  left: 38px;
  z-index: 3;
  color: #fff;
}
.avatar-caption span {
  display: inline-block;
  margin-bottom: 12px;
  color: #83b7ff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1.6px;
  text-transform: uppercase;
}
.avatar-caption p {
  max-width: 620px;
  margin: 0;
  font-family: "Noto Serif SC", "Songti SC", serif;
  font-size: clamp(18px, 2vw, 27px);
  font-weight: 600;
  line-height: 1.65;
  text-shadow: 0 2px 18px rgba(0,0,0,.35);
}

.avatar-start-card {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 5;
  display: grid;
  width: min(360px, calc(100% - 64px));
  justify-items: center;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(255,255,255,.18);
  border-radius: 18px;
  padding: 26px;
  color: #fff;
  background: rgba(7,18,34,.58);
  box-shadow: 0 20px 55px rgba(0,0,0,.2);
  text-align: center;
  backdrop-filter: blur(18px);
}
.avatar-start-card > span { color: #82b7ff; font-size: 9px; font-weight: 900; letter-spacing: 2px; }
.avatar-start-card h1 { margin: 9px 0 7px; font-size: 23px; }
.avatar-start-card p { margin: 0 0 18px; color: rgba(255,255,255,.68); font-size: 11px; line-height: 1.7; }
.avatar-start-card label { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; color: rgba(255,255,255,.76); font-size: 10px; }
.avatar-start-card select { border: 1px solid rgba(255,255,255,.2); border-radius: 8px; padding: 7px 25px 7px 9px; color: #fff; background: rgba(255,255,255,.1); }
.start-interview-button { border: 0; border-radius: 10px; padding: 11px 24px; color: #15345f; background: #fff; font-size: 11px; font-weight: 800; }
.start-interview-button:disabled { opacity: .55; }

.avatar-controls {
  position: absolute;
  right: 26px;
  bottom: 26px;
  z-index: 4;
  display: flex;
  gap: 7px;
  border: 1px solid rgba(255,255,255,.17);
  border-radius: 14px;
  padding: 6px;
  background: rgba(9,20,37,.58);
  backdrop-filter: blur(15px);
}
.avatar-controls button {
  display: grid;
  width: 38px;
  height: 36px;
  place-items: center;
  border: 0;
  border-radius: 9px;
  color: rgba(255,255,255,.88);
  background: transparent;
  font-size: 11px;
}
.avatar-controls button:hover, .avatar-controls button.active { color: #fff; background: rgba(255,255,255,.14); }
.avatar-controls button.active { box-shadow: inset 0 0 0 1px #ff7b7b; }
.avatar-controls button.muted { color: #ff9d9d; }
.avatar-controls button:disabled { opacity: .35; }

.human-camera {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 35%, rgba(70, 106, 151, .28), transparent 28%),
    #111c2b;
}
.human-camera video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
.human-camera:after { content: ''; position: absolute; inset: 0; z-index: 1; pointer-events: none; background: linear-gradient(180deg, rgba(7,15,29,.5), transparent 25%, transparent 62%, rgba(7,15,29,.78)); }
.human-stage-header { position: absolute; top: 0; right: 0; left: 0; z-index: 4; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 26px 28px; color: #fff; }
.human-identity { display: flex; align-items: center; gap: 11px; }
.human-identity > div { display: grid; gap: 3px; }
.human-identity strong { font-size: 14px; }
.human-identity small { color: rgba(255,255,255,.6); font-size: 10px; }
.camera-live-dot { width: 9px; height: 9px; border: 2px solid rgba(255,255,255,.5); border-radius: 50%; background: #8996a8; }
.camera-live-dot.ready { background: #43d79a; box-shadow: 0 0 0 5px rgba(67,215,154,.14); }
.interview-metrics { display: flex; gap: 7px; }
.interview-metrics span { border: 1px solid rgba(255,255,255,.15); border-radius: 999px; padding: 7px 10px; color: rgba(255,255,255,.72); background: rgba(7,18,33,.42); font-size: 9px; backdrop-filter: blur(12px); }
.interview-metrics b { color: #fff; font-size: 11px; }
.camera-start-state { position: absolute; inset: 0; z-index: 2; display: grid; align-content: center; justify-items: center; padding: 40px; color: #fff; text-align: center; }
.camera-start-state:before { content: ''; width: 70px; height: 52px; margin-bottom: 22px; border: 2px solid rgba(255,255,255,.48); border-radius: 17px; background: radial-gradient(circle, rgba(112,167,227,.9) 0 7px, transparent 8px); box-shadow: 0 0 50px rgba(83,143,211,.25); }
.camera-start-state > span { color: #77aee9; font-size: 9px; font-weight: 900; letter-spacing: 2px; }
.camera-start-state > b { margin-top: 8px; font-family: Georgia, 'Songti SC', serif; font-size: 24px; }
.camera-start-state > p { max-width: 380px; margin: 10px 0 22px; color: rgba(255,255,255,.62); font-size: 11px; line-height: 1.7; }
.camera-start-state > button { border: 1px solid rgba(255,255,255,.2); border-radius: 10px; padding: 11px 18px; color: #102238; background: #fff; font-size: 11px; font-weight: 800; }
.camera-overlay { position: absolute; top: 82px; right: 18px; left: 18px; z-index: 4; display: flex; align-items: center; justify-content: space-between; }
.camera-overlay span { display: flex; align-items: center; gap: 7px; border-radius: 99px; padding: 7px 10px; color: #fff; background: rgba(7,18,33,.62); backdrop-filter: blur(10px); font-size: 9px; }
.camera-overlay span i { width: 6px; height: 6px; border-radius: 50%; background: #8795a9; }
.camera-overlay span i.ready { background: #45dc9b; box-shadow: 0 0 0 4px rgba(69,220,155,.15); }
.camera-overlay > div { display: flex; align-items: center; gap: 7px; }
.camera-overlay select { max-width: 170px; height: 29px; border: 1px solid rgba(255,255,255,.2); border-radius: 8px; padding: 0 8px; color: #fff; background: rgba(7,18,33,.68); font-size: 9px; }
.camera-overlay button { border: 1px solid rgba(255,255,255,.25); border-radius: 9px; padding: 7px 10px; color: #fff; background: rgba(255,255,255,.12); font-size: 9px; }
.camera-live-error { position: absolute; top: 14px; right: 14px; left: 14px; z-index: 3; margin: 0; border: 1px solid rgba(255,189,171,.22); border-radius: 10px; padding: 10px 13px; color: #ffd3c7; background: rgba(74,24,18,.75); backdrop-filter: blur(10px); font-size: 10px; text-align: center; }
.nonverbal-status { position: absolute; top: 12px; left: 12px; z-index: 2; border-radius: 99px; padding: 6px 9px; color: rgba(255,255,255,.82); background: rgba(7,18,33,.62); backdrop-filter: blur(10px); font-size: 9px; }
.nonverbal-status.available { color: #baf6da; }
.nonverbal-status.unavailable { color: #ffd3c7; }

.interview-dock { position: absolute; right: 22px; bottom: 22px; left: 22px; z-index: 4; border: 1px solid rgba(255,255,255,.16); border-radius: 16px; padding: 12px; background: rgba(7,18,33,.74); box-shadow: 0 18px 50px rgba(0,0,0,.26); backdrop-filter: blur(18px); }
.dock-status { display: flex; align-items: center; justify-content: space-between; margin: 0 3px 8px; color: rgba(255,255,255,.72); font-size: 9px; }
.dock-status small { color: #8dbdff; }
.interview-dock textarea { width: 100%; height: 68px; resize: none; border: 1px solid rgba(255,255,255,.12); border-radius: 10px; padding: 10px 12px; outline: 0; color: #fff; background: rgba(255,255,255,.08); font-family: inherit; font-size: 11px; line-height: 1.6; }
.interview-dock textarea::placeholder { color: rgba(255,255,255,.45); }
.interview-dock textarea:focus { border-color: rgba(126,180,255,.6); }
.dock-actions { display: flex; align-items: center; gap: 8px; padding-top: 8px; }
.dock-actions > span { flex: 1; color: rgba(255,255,255,.4); font-size: 8px; }
.voice-input-button, .send-answer-button { border: 0; border-radius: 8px; padding: 9px 12px; font-size: 10px; font-weight: 700; }
.voice-input-button { color: #dce9fa; background: rgba(255,255,255,.12); }
.voice-input-button.recording { color: #ffc1c6; background: rgba(213,64,78,.22); }
.send-answer-button { color: #fff; background: #246bda; }
.send-answer-button:disabled { opacity: .45; }
.finish-avatar-button { flex: 0 0 auto; border: 0; padding: 8px 4px; color: rgba(255,255,255,.72); background: transparent; font-size: 9px; font-weight: 700; }
.finish-avatar-button:hover { color: #fff; }
.finish-avatar-button:disabled { color: rgba(255,255,255,.28); }
.avatar-error { position: absolute; right: 22px; bottom: 176px; left: 22px; z-index: 6; margin: 0; border-radius: 9px; padding: 9px 12px; color: #ffd6da; background: rgba(113,25,37,.78); font-size: 10px; text-align: center; backdrop-filter: blur(12px); }

@media (max-width: 1100px) {
  .avatar-page { height: auto; min-height: 100vh; grid-template-columns: 1fr; overflow: visible; }
  .avatar-stage-full, .human-panel { min-height: 680px; }
}

@media (max-width: 760px) {
  .avatar-page { padding: 8px; }
  .avatar-stage-full, .human-panel { min-height: 560px; border-radius: 18px; }
  .avatar-stage-header { padding: 20px; }
  .avatar-caption { right: 22px; bottom: 88px; left: 22px; }
  .avatar-caption p { font-size: 17px; }
  .avatar-controls { right: 18px; bottom: 18px; }
  .human-stage-header { align-items: flex-start; padding: 20px; }
  .interview-metrics { flex-wrap: wrap; justify-content: flex-end; }
  .camera-overlay { top: 92px; align-items: flex-start; gap: 8px; }
  .camera-overlay > div { flex-wrap: wrap; justify-content: flex-end; }
  .interview-dock { right: 14px; bottom: 14px; left: 14px; }
  .dock-actions { flex-wrap: wrap; }
  .dock-actions > span { display: none; }
}
</style>
