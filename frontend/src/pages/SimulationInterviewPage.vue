<script setup>
import { computed, nextTick, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, getSession } from '../api/client';

const router = useRouter();
const session = ref(getSession());
const conversationRef = ref(null);
const turn = ref(null);
const messages = ref([]);
const input = ref('');
const loading = ref(false);
const started = ref(false);
const error = ref('');
const stressLevel = ref('medium');

const isGroup = computed(() => session.value?.mode === 'group_interview');
const isStress = computed(() => session.value?.mode === 'stress_interview');
const title = computed(() =>
  isGroup.value ? '无领导小组讨论' : isStress.value ? '压力面试' : '正在返回场景选择'
);
const userMessageCount = computed(() => messages.value.filter((item) => item.speaker === 'user').length);

const groupStages = [
  ['case_intro', '案例介绍'],
  ['individual_statement', '个人陈述'],
  ['free_discussion', '自由讨论'],
  ['disagreement_resolution', '分歧处理'],
  ['consensus', '形成共识'],
  ['summary', '总结'],
  ['scoring', '评分']
];
const stressStages = [
  ['opening', '开场陈述'],
  ['probing', '连续追问'],
  ['closing', '结束复盘'],
  ['scoring', '综合评分']
];
const stageList = computed(() => isGroup.value ? groupStages : isStress.value ? stressStages : []);
const stageLabel = computed(() =>
  stageList.value.find(([key]) => key === turn.value?.stage)?.[1] || (turn.value?.stage === 'paused' ? '已暂停' : '准备中')
);

const roleNames = {
  interviewer: 'AI 面试官',
  candidate_logic: '陈析 · 逻辑分析型',
  candidate_collaboration: '周和 · 协调合作型',
  candidate_challenger: '秦问 · 质疑挑战型',
  user: '我'
};

onMounted(() => {
  if (!isGroup.value && !isStress.value) router.replace('/dashboard');
  else start();
});

function roleInitial(role) {
  return role === 'user' ? '我' : role === 'interviewer' ? '面' : role === 'candidate_logic' ? '析' : role === 'candidate_collaboration' ? '和' : '问';
}

async function scrollToBottom() {
  await nextTick();
  if (conversationRef.value) conversationRef.value.scrollTop = conversationRef.value.scrollHeight;
}

function appendMessages(items) {
  messages.value.push(...(items || []));
  scrollToBottom();
}

async function start() {
  if (!session.value || (!isGroup.value && !isStress.value)) {
    await router.push('/dashboard');
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const data = await api.startSimulation({
      session_id: session.value.session_id,
      mode: session.value.mode,
      stress_level: isStress.value ? stressLevel.value : null
    });
    turn.value = data;
    if (data.stress_level) stressLevel.value = data.stress_level;
    messages.value = [];
    appendMessages(data.messages);
    started.value = true;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function sendMessage(forcedMessage = null) {
  const content = (forcedMessage || input.value).trim();
  if (!content || !turn.value || loading.value || turn.value.status === 'completed') return;
  messages.value.push({
    message_id: `local-${Date.now()}`,
    speaker: 'user',
    display_name: '我',
    content
  });
  input.value = '';
  scrollToBottom();
  loading.value = true;
  error.value = '';
  try {
    const data = await api.handleSimulationMessage({
      session_id: session.value.session_id,
      turn_id: turn.value.turn_id,
      message: content
    });
    turn.value = data;
    if (data.stress_level) stressLevel.value = data.stress_level;
    appendMessages(data.messages);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function finish() {
  if (!userMessageCount.value || loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    await api.finishSimulation({ session_id: session.value.session_id });
    await api.generateSimulationReport({ session_id: session.value.session_id });
    await router.push('/report');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <LayoutShell>
    <main v-if="isGroup || isStress" class="simulation-page" :class="{ stress: isStress }">
      <header class="simulation-header">
        <button class="back-link" @click="router.push('/dashboard')"><AppIcon name="back" />返回场景</button>
        <div><span>{{ isGroup ? 'GROUP ASSESSMENT' : 'LIVE INTERVIEW' }}</span><h1>{{ title }}</h1></div>
        <div class="session-state"><i></i>{{ started ? stageLabel : '正在连接' }}</div>
      </header>

      <section v-if="!started" class="session-connecting">
        <div class="connecting-pulse"><i></i><i></i><i></i></div>
        <span>{{ isGroup ? 'ASSEMBLING PARTICIPANTS' : 'CONNECTING INTERVIEWER' }}</span>
        <h2>{{ isGroup ? '正在召集群面参与者' : '正在连接压力面试官' }}</h2>
        <p>{{ error || '正在准备本次会话，请稍候…' }}</p>
        <button v-if="error" class="outline-button" :disabled="loading" @click="start">重新连接</button>
      </section>

      <section v-else class="simulation-workspace" :class="{ 'stress-interview-workspace': isStress }">
        <aside v-if="isGroup" class="stage-rail">
          <span>SESSION FLOW</span>
          <ol><li v-for="([key, label], index) in stageList" :key="key" :class="{ active: turn?.stage === key, done: stageList.findIndex(([stage]) => stage === turn?.stage) > index }"><i></i>{{ label }}</li></ol>
        </aside>

        <div class="discussion-panel">
          <header v-if="isStress" class="stress-interviewer-banner">
            <div class="interviewer-mark">面</div>
            <div><span>AI INTERVIEWER</span><h2>压力面试官</h2></div>
            <div class="live-pressure"><i></i>当前压力：{{ { light: '轻度', medium: '中度', high: '高度' }[stressLevel] }}</div>
          </header>
          <div ref="conversationRef" class="discussion-stream">
            <article v-for="message in messages" :key="message.message_id" :class="['discussion-message', message.speaker]">
              <b>{{ roleInitial(message.speaker) }}</b>
              <div><header><strong>{{ message.display_name || roleNames[message.speaker] }}</strong><span v-if="message.reply_to">回应上一观点</span></header><p>{{ message.content }}</p></div>
            </article>
            <div v-if="loading" class="text-thinking"><i></i><i></i><i></i><span>正在组织回应</span></div>
          </div>

          <div v-if="isStress" class="stress-controls"><span>安全控制</span><button @click="sendMessage('降低压力')">降低压力</button><button @click="sendMessage('暂停')">暂停</button><button class="stop" @click="sendMessage('停止')">结束面试</button></div>
          <form class="discussion-composer" @submit.prevent="sendMessage()">
            <textarea v-model="input" :disabled="loading || turn?.status === 'completed'" :placeholder="turn?.status === 'completed' ? '会话已停止，请生成报告' : isGroup ? '输入你的观点、回应或总结…' : '输入回答，也可以直接输入控制口令…'" @keydown.enter.exact.prevent="sendMessage()"></textarea>
            <div><span>{{ input.length }}/10000</span><button class="primary-button" :disabled="!input.trim() || loading || turn?.status === 'completed'">发送发言</button></div>
          </form>
          <footer><p v-if="error" class="form-error">{{ error }}</p><span></span><button class="outline-button" :disabled="!userMessageCount || loading" @click="finish">结束并生成报告</button></footer>
        </div>
      </section>
    </main>
    <main v-else class="simulation-page invalid-session">正在返回场景选择...</main>
  </LayoutShell>
</template>

<style scoped>
.simulation-page { display: flex; height: 100vh; min-height: 0; flex-direction: column; overflow: hidden; padding: 34px; color: #1e2b3e; background: radial-gradient(circle at 75% 0, #e4f1ed 0, transparent 33%), #f2f5f3; }
.invalid-session { display: grid; place-items: center; color: #718078; }
.simulation-page.stress { background: radial-gradient(circle at 75% 0, #f4e8dc 0, transparent 34%), #f5f3ef; }
.simulation-header { display: grid; flex: 0 0 auto; grid-template-columns: 1fr auto 1fr; width: 100%; align-items: center; max-width: 1180px; margin: 0 auto 26px; }
.simulation-header > div:nth-child(2) { text-align: center; }
.simulation-header span { color: #37806c; font-size: 9px; font-weight: 900; letter-spacing: 2px; }
.stress .simulation-header span { color: #a75d3d; }
.simulation-header h1 { margin: 5px 0 0; font-family: Georgia, 'Songti SC', serif; font-size: 26px; }
.session-state { justify-self: end; display: flex; align-items: center; gap: 8px; border: 1px solid #d9e2dd; border-radius: 99px; padding: 8px 12px; background: rgba(255,255,255,.72); font-size: 11px; }
.session-state i { width: 7px; height: 7px; border-radius: 50%; background: #45a786; }
.session-connecting { display: grid; max-width: 760px; min-height: 520px; align-content: center; justify-items: center; margin: auto; border: 1px solid rgba(40,76,62,.12); border-radius: 24px; padding: 50px; background: rgba(255,255,255,.82); box-shadow: 0 20px 70px rgba(36,58,48,.08); text-align: center; }
.session-connecting > span { margin-top: 24px; color: #3f806b; font-size: 9px; font-weight: 900; letter-spacing: 2px; }.stress .session-connecting > span { color: #ac5a3b; }
.session-connecting h2 { margin: 9px 0; font-family: Georgia, 'Songti SC', serif; font-size: 28px; }.session-connecting p { margin: 0 0 20px; color: #7d8b84; font-size: 12px; }
.connecting-pulse { display: flex; gap: 8px; }.connecting-pulse i { width: 11px; height: 11px; border-radius: 50%; background: #409078; animation: connect-pulse .8s ease infinite alternate; }.connecting-pulse i:nth-child(2){animation-delay:.18s}.connecting-pulse i:nth-child(3){animation-delay:.36s}.stress .connecting-pulse i{background:#b45d3d}@keyframes connect-pulse{to{transform:translateY(-9px);opacity:.35}}
.simulation-workspace { display: grid; flex: 1 1 auto; grid-template-columns: 220px minmax(0, 1fr); width: 100%; max-width: 1180px; height: auto; min-height: 0; margin: 0 auto; overflow: hidden; border: 1px solid #dce5df; border-radius: 24px; background: #fff; box-shadow: 0 20px 70px rgba(36,58,48,.1); }
.stress-interview-workspace { grid-template-columns: minmax(0, 1fr); max-width: 980px; border-color: #ead8cf; box-shadow: 0 20px 70px rgba(91,53,36,.1); }
.stage-rail { padding: 34px 28px; color: #d8e8e2; background: #173d34; }.stress .stage-rail { color: #eadfd8; background: #4a3025; }.stage-rail > span { font-size: 9px; font-weight: 900; letter-spacing: 2px; opacity: .68; }
.stage-rail ol { display: grid; gap: 0; margin: 30px 0; padding: 0; list-style: none; }.stage-rail li { position: relative; padding: 0 0 28px 28px; font-size: 11px; opacity: .48; }.stage-rail li i { position: absolute; left: 0; top: 1px; width: 9px; height: 9px; border: 2px solid currentColor; border-radius: 50%; }.stage-rail li:after { content: ''; position: absolute; left: 5px; top: 13px; width: 1px; height: 22px; background: currentColor; opacity: .45; }.stage-rail li.active { color: #fff; font-weight: 800; opacity: 1; }.stage-rail li.active i, .stage-rail li.done i { background: #64d0aa; }.stage-rail li.done { opacity: .75; }
.pressure-meter { margin-top: 40px; border-top: 1px solid rgba(255,255,255,.14); padding-top: 20px; }.pressure-meter small { display: block; opacity: .6; }.pressure-meter b { display: block; margin: 6px 0 12px; color: #fff; }.pressure-meter div { height: 4px; overflow: hidden; border-radius: 9px; background: rgba(255,255,255,.13); }.pressure-meter i { display: block; height: 100%; background: #ef8d61; transition: width .4s; }
.discussion-panel { display: grid; grid-template-rows: minmax(0,1fr) auto auto auto; min-width: 0; min-height: 0; overflow: hidden; padding: 26px 34px 20px; }.discussion-stream { min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 10px 4px 20px; }.discussion-message { display: flex; max-width: 78%; gap: 12px; margin-bottom: 20px; }.discussion-message > b { display: grid; flex: 0 0 34px; height: 34px; place-items: center; border-radius: 11px; color: #fff; background: #2e6555; font-size: 11px; }.discussion-message > div { min-width: 0; }.discussion-message header { display: flex; align-items: center; gap: 10px; margin: 0 0 6px 3px; }.discussion-message header strong { font-size: 11px; }.discussion-message header span { color: #9a7662; font-size: 9px; }.discussion-message p { margin: 0; border-radius: 4px 15px 15px; padding: 13px 16px; color: #425149; background: #f0f5f2; font-size: 13px; line-height: 1.75; }.discussion-message.user { flex-direction: row-reverse; margin-left: auto; }.discussion-message.user > b { color: #466157; background: #e2ebe6; }.discussion-message.user header { justify-content: flex-end; }.discussion-message.user p { border-radius: 15px 4px 15px 15px; color: #fff; background: #28725d; }.discussion-message.candidate_logic > b { background: #29649b; }.discussion-message.candidate_collaboration > b { background: #388061; }.discussion-message.candidate_challenger > b { background: #ad673b; }.stress .discussion-message.interviewer > b { background: #a45233; }.stress .discussion-message.interviewer p { background: #fff1e9; }
.stress-interview-workspace .discussion-panel { grid-template-rows: auto minmax(0,1fr) auto auto auto; padding-top: 0; }
.stress-interviewer-banner { display: flex; align-items: center; gap: 13px; border-bottom: 1px solid #eee1da; padding: 20px 0; }.interviewer-mark { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 50%; color: #fff; background: #a85234; font-size: 12px; font-weight: 800; }.stress-interviewer-banner > div:nth-child(2) { display: grid; gap: 3px; }.stress-interviewer-banner span { color: #b07158; font-size: 8px; font-weight: 900; letter-spacing: 1.4px; }.stress-interviewer-banner h2 { margin: 0; font-size: 15px; }.live-pressure { display: flex; align-items: center; gap: 7px; margin-left: auto; border-radius: 99px; padding: 7px 11px; color: #8c5a46; background: #fff1e9; font-size: 10px; }.live-pressure i { width: 6px; height: 6px; border-radius: 50%; background: #d26b45; }
.text-thinking { display: flex; align-items: center; gap: 4px; padding: 8px 46px; color: #8b9992; font-size: 10px; }.text-thinking i { width: 5px; height: 5px; border-radius: 50%; background: #4b8d77; animation: dot .7s infinite alternate; }.text-thinking i:nth-child(2){animation-delay:.15s}.text-thinking i:nth-child(3){animation-delay:.3s;margin-right:6px}@keyframes dot{to{transform:translateY(-4px);opacity:.4}}
.stress-controls { display: flex; align-items: center; gap: 8px; padding: 0 0 12px; }.stress-controls span { color: #8d817a; font-size: 10px; }.stress-controls button { border: 1px solid #e5d9d1; border-radius: 99px; padding: 6px 11px; color: #7a5d4e; background: #fffaf7; font-size: 10px; }.stress-controls button.stop { color: #b53f42; }
.discussion-composer { border: 1px solid #dbe5df; border-radius: 15px; padding: 8px; box-shadow: 0 8px 24px rgba(36,64,51,.06); }.discussion-composer textarea { width: 100%; height: 74px; resize: none; border: 0; padding: 10px; outline: 0; font-family: inherit; }.discussion-composer > div { display: flex; align-items: center; border-top: 1px solid #edf1ef; padding: 7px 4px 0; }.discussion-composer span { flex: 1; color: #a3ada8; font-size: 9px; }.discussion-composer button { padding: 9px 16px; }.discussion-panel footer { display: flex; min-height: 42px; align-items: center; padding-top: 10px; }.discussion-panel footer span { flex: 1; }.discussion-panel footer p { margin: 0; }
@media(max-width:900px){.simulation-page{height:100dvh;padding:20px 12px}.simulation-header{grid-template-columns:1fr auto}.simulation-header>div:nth-child(2){text-align:right}.session-state{display:none}.session-connecting{min-height:0;padding:35px 22px}.simulation-workspace{grid-template-columns:1fr;height:auto;min-height:0}.stage-rail{display:none}.discussion-panel{min-height:0;padding:20px 16px}.stress-interview-workspace .discussion-panel{padding-top:0}.discussion-message{max-width:92%}}
</style>
