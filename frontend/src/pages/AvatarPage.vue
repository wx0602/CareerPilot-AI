<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import { api, getSession, setSession } from '../api/client';
import interviewerImage from '../assets/ai-interviewer-lin.png';

const router = useRouter();
const stageRef = ref(null);
const messageListRef = ref(null);
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
let recognition = null;

const statusText = computed(() => {
  if (listening.value) return '正在聆听';
  if (speaking.value) return '正在提问';
  if (loading.value) return '正在思考';
  if (started.value) return '等待回答';
  return '准备就绪';
});

const interviewTitle = computed(
  () => session.value?.learning_module_title || session.value?.position || '职业能力面试'
);

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
  window.speechSynthesis?.cancel();
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = null;
  recognition?.abort();
});

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

function addMessage(role, text, meta = null) {
  messages.value.push({ role, text, meta, id: `${Date.now()}-${messages.value.length}` });
  scrollToLatest();
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
    const data = await api.interviewMessage({ session_id: currentSession.session_id });
    currentQuestion.value = data.next_question;
    started.value = true;
    messages.value = [];
    addMessage('ai', data.next_question.question, data.is_followup ? '追问' : '面试问题');
    speak(data.next_question.question);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function submitAnswer() {
  const content = answer.value.trim();
  if (!content || !currentQuestion.value || loading.value) return;
  window.speechSynthesis?.cancel();
  addMessage('user', content);
  answer.value = '';
  loading.value = true;
  error.value = '';
  try {
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
      addMessage(
        'feedback',
        `本轮 ${data.evaluation.score} 分。亮点：${strengths}。建议改进：${weaknesses}。`,
        '即时反馈'
      );
    }
    currentQuestion.value = data.next_question;
    addMessage('ai', data.next_question.question, data.is_followup ? '针对性追问' : '下一题');
    speak(data.next_question.question);
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
  } else if (currentQuestion.value) {
    speak(currentQuestion.value.question);
  }
}

function replayQuestion() {
  if (currentQuestion.value) speak(currentQuestion.value.question);
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
            <div><strong>林悦</strong><small>CareerPilot AI 面试官</small></div>
          </div>
          <span class="avatar-status"><i></i>{{ statusText }}</span>
        </header>

        <div v-if="speaking || listening" class="voice-orbit" aria-hidden="true">
          <i v-for="n in 20" :key="n" :style="{ '--i': n }"></i>
        </div>

        <div class="avatar-caption">
          <span>{{ started ? interviewTitle : 'AI 实景模拟面试' }}</span>
          <p>
            {{ currentQuestion?.question || '我会根据你的目标岗位进行提问、追问与即时评分。准备好后，我们正式开始。' }}
          </p>
        </div>

        <div class="avatar-controls">
          <button :class="{ active: listening }" :title="listening ? '停止录音' : '语音回答'" @click="toggleListening">{{ listening ? '■' : '●' }}</button>
          <button :class="{ muted: !voiceEnabled }" :title="voiceEnabled ? '关闭声音' : '打开声音'" @click="toggleVoice">{{ voiceEnabled ? '◖))' : '◖×' }}</button>
          <button title="重播问题" :disabled="!currentQuestion" @click="replayQuestion">↻</button>
          <button title="全屏显示" @click="toggleFullscreen">⛶</button>
        </div>
      </div>

      <aside class="avatar-console">
        <header class="avatar-console-header">
          <div><span>LIVE INTERVIEW</span><h1>数字人模拟面试</h1></div>
          <div class="interview-metrics">
            <span>已答 <b>{{ answeredCount }}</b></span>
            <span v-if="latestScore !== null">本轮 <b>{{ latestScore }}</b></span>
          </div>
        </header>

        <div v-if="!started" class="avatar-welcome">
          <span class="welcome-mark">AI</span>
          <h2>不再只是一个展示形象</h2>
          <p>林悦会调用真实面试服务，根据你的回答进行评分与追问，同时支持语音朗读和语音输入。</p>
          <ul>
            <li><span>01</span>岗位定向提问</li>
            <li><span>02</span>回答即时分析</li>
            <li><span>03</span>训练报告沉淀</li>
          </ul>
          <button class="primary-button avatar-start-button" :disabled="loading" @click="startInterview">
            {{ loading ? '正在连接面试官...' : '开始数字人面试' }}
          </button>
        </div>

        <template v-else>
          <div ref="messageListRef" class="avatar-messages">
            <article v-for="message in messages" :key="message.id" :class="['avatar-message', message.role]">
              <span>{{ message.role === 'user' ? '我' : message.role === 'feedback' ? '评' : '林' }}</span>
              <div><small v-if="message.meta">{{ message.meta }}</small><p>{{ message.text }}</p></div>
            </article>
            <div v-if="loading" class="avatar-thinking"><i></i><i></i><i></i><span>正在分析你的回答</span></div>
          </div>

          <form class="avatar-composer" @submit.prevent="submitAnswer">
            <textarea
              v-model="answer"
              :disabled="loading"
              placeholder="输入回答，或点击麦克风使用语音输入…"
              @keydown.enter.exact.prevent="submitAnswer"
            ></textarea>
            <div>
              <button type="button" class="voice-input-button" :class="{ recording: listening }" @click="toggleListening">
                {{ listening ? '停止聆听' : '语音输入' }}
              </button>
              <span>{{ answer.length }}/10000</span>
              <button class="send-answer-button" type="submit" :disabled="!answer.trim() || loading">发送回答 ↑</button>
            </div>
          </form>

          <div class="avatar-session-actions">
            <div class="avatar-voice-settings">
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
  grid-template-rows: auto minmax(0, 1fr) auto auto;
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

.avatar-console-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid #e5eaf1;
  padding-bottom: 22px;
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
.avatar-message.user { flex-direction: row-reverse; margin-left: auto; }
.avatar-message.user > span { color: #4e6078; background: #e7ebf1; }
.avatar-message.user p { border-radius: 14px 4px 14px 14px; color: #fff; background: #246bda; }
.avatar-message.user small { text-align: right; }
.avatar-message.feedback { max-width: 96%; }
.avatar-message.feedback > span { color: #1b8c67; background: #dcf7ec; }
.avatar-message.feedback p { border: 1px solid #dceee8; color: #386356; background: #f1faf7; }

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
  .avatar-console { min-height: 690px; border: 1px solid #dce3ec; border-top: 0; border-radius: 0 0 22px 22px; }
}

@media (max-width: 760px) {
  .avatar-page { padding: 8px; }
  .avatar-stage-full { min-height: 520px; border-radius: 18px 18px 0 0; }
  .avatar-stage-header { padding: 20px; }
  .avatar-caption { right: 22px; bottom: 88px; left: 22px; }
  .avatar-caption p { font-size: 17px; }
  .avatar-controls { right: 18px; bottom: 18px; }
  .avatar-console { min-height: 680px; border-radius: 0 0 18px 18px; padding: 24px 18px; }
  .avatar-console-header { align-items: flex-start; flex-direction: column; }
  .avatar-session-actions { align-items: flex-start; flex-direction: column; }
  .avatar-voice-settings { width: 100%; flex-wrap: wrap; }
  .finish-avatar-button { align-self: flex-end; }
}
</style>
