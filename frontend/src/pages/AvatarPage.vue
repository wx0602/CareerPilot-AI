<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import { api, getSession, setSession } from '../api/client';
import interviewerImage from '../assets/ai-interviewer-lin.png';

const router = useRouter();
const stageRef = ref(null);
const messageListRef = ref(null);
const videoRef = ref(null);
const session = ref(getSession());
const messages = ref([]);
const currentQuestion = ref(null);
const answer = ref('');
const loading = ref(false);
const streaming = ref(false);
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
let recognition = null;
let cameraStream = null;
let streamVersion = 0;

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
  recognition.onresult = (event) => {
    answer.value = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join('');
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
  streamVersion += 1;
  window.speechSynthesis?.cancel();
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = null;
  recognition?.abort();
  cameraStream?.getTracks().forEach((track) => track.stop());
});

async function startCamera() {
  cameraError.value = '';
  cameraReady.value = false;
  cameraResolution.value = '';
  if (!window.isSecureContext) {
    cameraError.value = '摄像头需要 HTTPS，或使用 localhost / 127.0.0.1 访问。';
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = '当前浏览器不支持摄像头访问。';
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
      cameraActive.value = false;
      cameraReady.value = false;
      cameraError.value = '摄像头连接已中断，请重新开启。';
    };
    track.onmute = () => {
      cameraReady.value = false;
      cameraError.value = '摄像头暂时没有输出画面，请检查是否被其他程序占用或物理遮挡。';
    };
    track.onunmute = () => {
      cameraError.value = '';
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
  } catch (err) {
    cameraStream?.getTracks().forEach((track) => track.stop());
    cameraStream = null;
    cameraActive.value = false;
    cameraReady.value = false;
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
  cameraStream?.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  if (videoRef.value) videoRef.value.srcObject = null;
  cameraActive.value = false;
  cameraReady.value = false;
  cameraResolution.value = '';
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

async function scrollToLatest() {
  await nextTick();
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
  }
}

function addMessage(role, text, meta = null, displayName = null) {
  messages.value.push({ role, text, meta, displayName, id: `${Date.now()}-${messages.value.length}` });
  scrollToLatest();
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function streamMessage(role, content, meta = null, displayName = null) {
  const version = ++streamVersion;
  const message = reactive({
    role,
    text: '',
    meta,
    displayName,
    streaming: true,
    id: `${Date.now()}-${messages.value.length}`
  });
  messages.value.push(message);
  streaming.value = true;

  for (const character of Array.from(content || '')) {
    if (version !== streamVersion) return;
    message.text += character;
    await scrollToLatest();
    await wait(streamDelay(character));
  }

  message.streaming = false;
  streaming.value = false;
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
  };
  utterance.onend = utterance.onerror = () => {
    speaking.value = false;
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
    started.value = true;
    messages.value = [];
    speak(data.next_question.question);
    await streamMessage('ai', data.next_question.question, data.is_followup ? '追问' : '面试问题');
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
    speak(data.next_question.question);
    await streamMessage('ai', data.next_question.question, data.is_followup ? '针对性追问' : '下一题');
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
  window.speechSynthesis?.cancel();
  recognition.start();
  listening.value = true;
}

function toggleVoice() {
  voiceEnabled.value = !voiceEnabled.value;
  if (!voiceEnabled.value) {
    window.speechSynthesis?.cancel();
    speaking.value = false;
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
    await api.generateReport({ session_id: session.value.session_id });
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

        <div class="avatar-controls">
          <button :class="{ active: listening }" :title="listening ? '停止录音' : '语音回答'" @click="toggleListening">{{ listening ? '■' : '●' }}</button>
          <button :class="{ muted: !voiceEnabled }" :title="voiceEnabled ? '关闭声音' : '打开声音'" @click="toggleVoice">{{ voiceEnabled ? '◖))' : '◖×' }}</button>
          <button title="重播问题" :disabled="!currentPrompt" @click="replayQuestion">↻</button>
          <button title="全屏显示" @click="toggleFullscreen">⛶</button>
        </div>
      </div>

      <aside class="avatar-console">
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
          <p v-if="cameraActive && cameraError" class="camera-live-error">{{ cameraError }}</p>
        </section>

        <header class="avatar-console-header">
          <div><span>LIVE INTERVIEW</span><h1>{{ interviewTitle }}</h1></div>
          <div class="interview-metrics">
            <span>已答 <b>{{ answeredCount }}</b></span>
            <span v-if="latestScore !== null">本轮 <b>{{ latestScore }}</b></span>
            <span v-if="simulationTurn">阶段 <b>{{ stageLabels[simulationTurn.stage] }}</b></span>
          </div>
        </header>

        <div v-if="!started" class="avatar-welcome">
          <span class="welcome-mark">AI</span>
          <h2>{{ isGroupInterview ? '进入五人无领导小组讨论' : isStressInterview ? '开始安全可控的压力面试' : '不再只是一个展示形象' }}</h2>
          <p v-if="isGroupInterview">你将与逻辑分析型、协调合作型和质疑挑战型三名 AI 候选人共同讨论，AI 面试官负责推进流程。</p>
          <p v-else-if="isStressInterview">面试官会针对空泛、矛盾和证据不足连续追问。你可以随时输入“停止”“暂停”或“降低压力”。</p>
          <p v-else>林悦会调用真实面试服务，根据你的回答进行评分与追问，同时支持语音朗读和语音输入。</p>
          <label v-if="isStressInterview" class="stress-level-picker">
            初始压力等级
            <select v-model="stressLevel">
              <option value="light">轻度</option>
              <option value="medium">中度</option>
              <option value="high">高度</option>
            </select>
          </label>
          <ul>
            <li><span>01</span>岗位定向提问</li>
            <li><span>02</span>回答即时分析</li>
            <li><span>03</span>训练报告沉淀</li>
          </ul>
          <button class="primary-button avatar-start-button" :disabled="loading" @click="startInterview">
            {{ loading ? '正在连接面试官...' : `开始${interviewTitle}` }}
          </button>
        </div>

        <template v-else>
          <div ref="messageListRef" class="avatar-messages">
            <article v-for="message in messages" :key="message.id" :class="['avatar-message', message.role]">
              <span>{{ message.role === 'user' ? '我' : message.role === 'feedback' ? '评' : message.displayName?.slice(0, 1) || 'AI' }}</span>
              <div><small>{{ message.displayName || message.meta }}</small><p :class="{ streaming: message.streaming }">{{ message.text }}</p></div>
            </article>
            <div v-if="loading && !streaming" class="avatar-thinking"><i></i><i></i><i></i><span>正在分析你的回答</span></div>
          </div>

          <form class="avatar-composer" @submit.prevent="submitAnswer">
            <textarea
              v-model="answer"
              :disabled="loading || simulationStatus === 'completed'"
              :placeholder="simulationStatus === 'completed' ? '面试已停止，请生成报告' : '输入回答，或点击麦克风使用语音输入…'"
              @keydown.enter.exact.prevent="submitAnswer"
            ></textarea>
            <div>
              <button type="button" class="voice-input-button" :class="{ recording: listening }" @click="toggleListening">
                {{ listening ? '停止聆听' : '语音输入' }}
              </button>
              <span>{{ answer.length }}/10000</span>
              <button class="send-answer-button" type="submit" :disabled="!answer.trim() || loading || simulationStatus === 'completed'">发送回答 ↑</button>
            </div>
          </form>

          <div class="avatar-session-actions">
            <div class="avatar-voice-settings">
              <template v-if="isStressInterview">
                <label>压力</label>
                <strong class="current-stress-level">{{ { light: '轻度', medium: '中度', high: '高度' }[stressLevel] }}</strong>
              </template>
              <label>声音</label>
              <select v-model="selectedVoice" :disabled="!speechSupported">
                <option v-if="!voices.length" value="">系统默认中文音色</option>
                <option v-for="voice in voices" :key="voice.name" :value="voice.name">{{ voice.name }}</option>
              </select>
              <label>语速</label>
              <input v-model="speechRate" type="range" min="0.8" max="1.4" step="0.1" />
            </div>
            <button class="finish-avatar-button" :disabled="loading || !answeredCount" @click="finishInterview">结束并生成报告</button>
          </div>
        </template>

        <p v-if="error" class="avatar-error">{{ error }}</p>
      </aside>
    </section>
  </LayoutShell>
</template>

<style scoped>
.avatar-page {
  display: grid;
  grid-template-columns: minmax(400px, 0.92fr) minmax(460px, 1.08fr);
  min-height: 100vh;
  padding: 22px;
  gap: 0;
  background: #e9eef5;
}

.avatar-stage-full {
  position: relative;
  display: block;
  min-height: calc(100vh - 44px);
  overflow: hidden;
  border-radius: 24px 0 0 24px;
  background: #111c2c;
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
  bottom: 96px;
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

.avatar-console {
  position: relative;
  display: grid;
  grid-template-rows: minmax(360px, 48vh) auto minmax(0, 1fr) auto auto;
  min-width: 0;
  min-height: calc(100vh - 44px);
  overflow: hidden;
  border: 1px solid #dce3ec;
  border-left: 0;
  border-radius: 0 24px 24px 0;
  padding: 30px 32px;
  background: #fbfcfe;
  box-shadow: 18px 16px 45px rgba(35,53,78,.1);
}

.human-camera {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border-radius: 16px;
  background:
    radial-gradient(circle at 50% 35%, rgba(70, 106, 151, .28), transparent 28%),
    #111c2b;
}
.human-camera video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
.camera-start-state { position: absolute; inset: 0; z-index: 2; display: grid; align-content: center; justify-items: center; padding: 40px; color: #fff; text-align: center; }
.camera-start-state:before { content: ''; width: 70px; height: 52px; margin-bottom: 22px; border: 2px solid rgba(255,255,255,.48); border-radius: 17px; background: radial-gradient(circle, rgba(112,167,227,.9) 0 7px, transparent 8px); box-shadow: 0 0 50px rgba(83,143,211,.25); }
.camera-start-state > span { color: #77aee9; font-size: 9px; font-weight: 900; letter-spacing: 2px; }
.camera-start-state > b { margin-top: 8px; font-family: Georgia, 'Songti SC', serif; font-size: 24px; }
.camera-start-state > p { max-width: 380px; margin: 10px 0 22px; color: rgba(255,255,255,.62); font-size: 11px; line-height: 1.7; }
.camera-start-state > button { border: 1px solid rgba(255,255,255,.2); border-radius: 10px; padding: 11px 18px; color: #102238; background: #fff; font-size: 11px; font-weight: 800; }
.camera-overlay { position: absolute; right: 14px; bottom: 12px; left: 14px; display: flex; align-items: center; justify-content: space-between; }
.camera-overlay span { display: flex; align-items: center; gap: 7px; border-radius: 99px; padding: 7px 10px; color: #fff; background: rgba(7,18,33,.62); backdrop-filter: blur(10px); font-size: 9px; }
.camera-overlay span i { width: 6px; height: 6px; border-radius: 50%; background: #8795a9; }
.camera-overlay span i.ready { background: #45dc9b; box-shadow: 0 0 0 4px rgba(69,220,155,.15); }
.camera-overlay > div { display: flex; align-items: center; gap: 7px; }
.camera-overlay select { max-width: 170px; height: 29px; border: 1px solid rgba(255,255,255,.2); border-radius: 8px; padding: 0 8px; color: #fff; background: rgba(7,18,33,.68); font-size: 9px; }
.camera-overlay button { border: 1px solid rgba(255,255,255,.25); border-radius: 9px; padding: 7px 10px; color: #fff; background: rgba(255,255,255,.12); font-size: 9px; }
.camera-live-error { position: absolute; top: 14px; right: 14px; left: 14px; z-index: 3; margin: 0; border: 1px solid rgba(255,189,171,.22); border-radius: 10px; padding: 10px 13px; color: #ffd3c7; background: rgba(74,24,18,.75); backdrop-filter: blur(10px); font-size: 10px; text-align: center; }

.avatar-console-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid #e5eaf1;
  padding: 20px 0 18px;
}
.avatar-console-header > div:first-child { display: grid; gap: 6px; }
.avatar-console-header > div:first-child > span { color: #3475da; font-size: 9px; font-weight: 900; letter-spacing: 2px; }
.avatar-console-header h1 { margin: 0; color: #17253a; font-size: 21px; }
.interview-metrics { display: flex; gap: 8px; }
.interview-metrics span { border-radius: 8px; padding: 8px 10px; color: #78869a; background: #f0f3f7; font-size: 10px; }
.interview-metrics b { color: #236bd2; font-size: 14px; }

.avatar-welcome {
  display: grid;
  max-width: 520px;
  align-content: center;
  justify-items: start;
  margin: auto;
  padding: 40px 18px;
}
.welcome-mark {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, #1a5fca, #5897ee);
  box-shadow: 0 10px 25px rgba(36,104,207,.24);
  font-size: 12px;
  font-weight: 900;
}
.avatar-welcome h2 { margin: 22px 0 10px; color: #17253a; font-size: 24px; }
.avatar-welcome p { margin: 0; color: #718096; font-size: 13px; line-height: 1.8; }
.avatar-welcome ul { display: grid; width: 100%; gap: 0; margin: 25px 0; padding: 0; list-style: none; }
.avatar-welcome li { display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #edf0f4; padding: 12px 0; color: #47566c; font-size: 12px; }
.avatar-welcome li span { color: #8ba2c2; font-family: Georgia, serif; font-size: 11px; }
.avatar-start-button { min-width: 190px; padding: 13px 22px; }
.stress-level-picker { display: flex; align-items: center; gap: 12px; margin: 0 0 22px; color: #53647b; font-size: 11px; font-weight: 700; }
.stress-level-picker select { border: 1px solid #dce3ec; border-radius: 8px; padding: 8px 28px 8px 10px; color: #34465f; background: #fff; }
.current-stress-level { border-radius: 99px; padding: 5px 9px; color: #a4512d; background: #fff0e7; font-size: 9px; }

.avatar-messages {
  min-height: 0;
  overflow-y: auto;
  padding: 24px 5px 12px;
  scrollbar-width: thin;
  scrollbar-color: #d7dee8 transparent;
}
.avatar-message { display: flex; max-width: 88%; gap: 10px; margin: 0 0 18px; }
.avatar-message > span {
  display: grid;
  flex: 0 0 30px;
  height: 30px;
  place-items: center;
  border-radius: 10px;
  color: #fff;
  background: #203b63;
  font-size: 10px;
  font-weight: 800;
}
.avatar-message > div { min-width: 0; }
.avatar-message small { display: block; margin: 0 0 5px 2px; color: #8996a9; font-size: 9px; font-weight: 700; letter-spacing: .5px; }
.avatar-message p { margin: 0; border-radius: 4px 14px 14px; padding: 12px 15px; color: #425168; background: #eef2f7; font-size: 12px; line-height: 1.75; }
.avatar-message p.streaming::after {
  content: '';
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 3px;
  vertical-align: -2px;
  background: currentColor;
  animation: avatar-stream-cursor .65s steps(1) infinite;
}
@keyframes avatar-stream-cursor { 50% { opacity: 0; } }
.avatar-message.user { flex-direction: row-reverse; margin-left: auto; }
.avatar-message.user > span { color: #4e6078; background: #e7ebf1; }
.avatar-message.user p { border-radius: 14px 4px 14px 14px; color: #fff; background: #246bda; }
.avatar-message.user small { text-align: right; }
.avatar-message.feedback { max-width: 96%; }
.avatar-message.feedback > span { color: #1b8c67; background: #dcf7ec; }
.avatar-message.feedback p { border: 1px solid #dceee8; color: #386356; background: #f1faf7; }
.avatar-message.candidate_logic > span { background: #1f5c9f; }
.avatar-message.candidate_collaboration > span { background: #1b8a68; }
.avatar-message.candidate_challenger > span { background: #b6652c; }
.avatar-message.interviewer > span { background: #594d9d; }
.avatar-message.candidate_logic p { background: #edf5ff; }
.avatar-message.candidate_collaboration p { background: #edf9f5; }
.avatar-message.candidate_challenger p { background: #fff5eb; }

.avatar-thinking { display: flex; align-items: center; gap: 4px; padding: 8px 40px; color: #8a97a8; font-size: 10px; }
.avatar-thinking i { width: 4px; height: 4px; border-radius: 50%; background: #5988d1; animation: thinking-dot .7s ease infinite alternate; }
.avatar-thinking i:nth-child(2) { animation-delay: .15s; }
.avatar-thinking i:nth-child(3) { animation-delay: .3s; margin-right: 5px; }
@keyframes thinking-dot { to { transform: translateY(-4px); opacity: .35; } }

.avatar-composer {
  border: 1px solid #dbe2ec;
  border-radius: 14px;
  padding: 7px;
  background: #fff;
  box-shadow: 0 8px 25px rgba(36,58,91,.07);
}
.avatar-composer textarea { width: 100%; height: 72px; resize: none; border: 0; padding: 11px 12px; outline: 0; color: #35445b; background: transparent; font-family: inherit; font-size: 12px; line-height: 1.6; }
.avatar-composer > div { display: flex; align-items: center; gap: 10px; border-top: 1px solid #eef1f5; padding: 7px 6px 0; }
.avatar-composer > div > span { flex: 1; color: #a1abba; font-size: 9px; }
.voice-input-button, .send-answer-button { border: 0; border-radius: 8px; padding: 9px 12px; font-size: 10px; font-weight: 700; }
.voice-input-button { color: #5b6c83; background: #f1f4f8; }
.voice-input-button.recording { color: #b83e48; background: #ffeaec; }
.send-answer-button { color: #fff; background: #246bda; }
.send-answer-button:disabled { opacity: .45; }

.avatar-session-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding-top: 15px; }
.avatar-voice-settings { display: flex; min-width: 0; align-items: center; gap: 7px; }
.avatar-voice-settings label { color: #8a96a8; font-size: 9px; }
.avatar-voice-settings select { max-width: 130px; height: 30px; border: 1px solid #e0e5ec; border-radius: 7px; padding: 0 7px; color: #5a687d; background: #fff; font-size: 9px; }
.avatar-voice-settings input { width: 65px; accent-color: #246bda; }
.finish-avatar-button { flex: 0 0 auto; border: 0; padding: 8px 0; color: #68778c; background: transparent; font-size: 10px; font-weight: 700; }
.finish-avatar-button:hover { color: #246bda; }
.finish-avatar-button:disabled { color: #b8c0cb; }
.avatar-error { position: absolute; right: 32px; bottom: 7px; left: 32px; margin: 0; color: #c6424d; font-size: 10px; text-align: center; }

@media (max-width: 1100px) {
  .avatar-page { grid-template-columns: 1fr; }
  .avatar-stage-full { min-height: 620px; border-radius: 22px 22px 0 0; }
  .avatar-console { grid-template-rows: 420px auto minmax(400px, 1fr) auto auto; min-height: 1050px; border: 1px solid #dce3ec; border-top: 0; border-radius: 0 0 22px 22px; }
}

@media (max-width: 760px) {
  .avatar-page { padding: 8px; }
  .avatar-stage-full { min-height: 520px; border-radius: 18px 18px 0 0; }
  .avatar-stage-header { padding: 20px; }
  .avatar-caption { right: 22px; bottom: 88px; left: 22px; }
  .avatar-caption p { font-size: 17px; }
  .avatar-controls { right: 18px; bottom: 18px; }
  .avatar-console { grid-template-rows: 320px auto minmax(420px, 1fr) auto auto; min-height: 980px; border-radius: 0 0 18px 18px; padding: 18px; }
  .avatar-console-header { align-items: flex-start; flex-direction: column; }
  .avatar-session-actions { align-items: flex-start; flex-direction: column; }
  .avatar-voice-settings { width: 100%; flex-wrap: wrap; }
  .finish-avatar-button { align-self: flex-end; }
}
</style>
