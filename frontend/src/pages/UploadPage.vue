<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, getSession, setSession } from '../api/client';

const router = useRouter();
const route = useRoute();
const isPitch = computed(() => route.query.flow === 'pitch');
const materialType = ref(isPitch.value ? 'pitch_ppt' : 'resume');
const active = ref(isPitch.value ? '路演 PPT' : '简历');
const interviewExperience = ref('avatar');
const file = ref(null);
const status = ref('');
const error = ref('');
const session = ref(getSession());
const preparing = ref(false);

const types = computed(() => isPitch.value
  ? [
      { label: '路演 PPT', value: 'pitch_ppt' },
      { label: '商业计划书', value: 'business_plan' },
      { label: '项目介绍', value: 'project_intro' }
    ]
  : [
      { label: '简历', value: 'resume' },
      { label: '职位描述（JD）', value: 'jd' }
    ]
);
const acceptedFiles = computed(() => isPitch.value ? '.pptx,.pdf,.doc,.docx,.txt' : '.pdf,.doc,.docx,.txt');
const destination = computed(() => isPitch.value ? '/interview' : interviewExperience.value === 'text' ? '/interview' : '/avatar');
const destinationLabel = computed(() => isPitch.value ? '路演答辩' : interviewExperience.value === 'text' ? '文本面试' : '数字人面试');

onMounted(async () => {
  if (route.query.new === '1') {
    await ensureInterviewSession(true);
    await router.replace({ path: '/upload', query: isPitch.value ? { flow: 'pitch' } : {} });
  }
});

function setType(type) {
  active.value = type.label;
  materialType.value = type.value;
}

function choose(event) {
  file.value = event.target.files?.[0] || null;
  status.value = '';
  error.value = '';
}

async function ensureInterviewSession(forceNew = false) {
  const requiredMode = isPitch.value ? 'pitch' : 'job';
  if (session.value?.mode === requiredMode && !forceNew) return session.value;
  preparing.value = true;
  error.value = '';
  try {
    const created = await api.createSession({
      mode: requiredMode,
      position: isPitch.value ? '项目路演' : '目标岗位',
      company: null
    });
    setSession(created);
    session.value = created;
    return created;
  } catch (err) {
    error.value = err.message;
    return null;
  } finally {
    preparing.value = false;
  }
}

async function upload() {
  if (!file.value) return;
  const currentSession = await ensureInterviewSession();
  if (!currentSession) return;
  status.value = '上传解析中...';
  error.value = '';
  try {
    const result = await api.uploadMaterial({
      sessionId: currentSession.session_id,
      materialType: materialType.value,
      file: file.value
    });
    status.value = `解析状态：${result.parse_status}`;
    if (result.parse_status === 'parsed') {
      await router.push(destination.value);
    }
  } catch (err) {
    error.value = err.message;
    status.value = '';
  }
}

async function goInterview() {
  const currentSession = await ensureInterviewSession();
  if (currentSession) await router.push(destination.value);
}
</script>

<template>
  <LayoutShell>
    <section class="page upload-page">
      <header>
        <h1>{{ isPitch ? '上传路演材料' : '上传求职材料' }}</h1>
        <p>{{ isPitch ? '上传 PPT、商业计划书或项目介绍后，AI 评委会结合材料进行路演质询。' : '上传简历或职位描述后，可选择文本面试或数字人面试。' }}</p>
      </header>

      <div class="upload-summary">
        <span>训练流程</span>
        <b>材料解析 → {{ isPitch ? '路演答辩' : '选择面试模式' }} → 自动生成报告</b>
        <small>{{ isPitch ? '支持路演 PPT、商业计划书和项目介绍。' : '简历材料只用于面试，不参与企业笔试组卷。' }}</small>
      </div>

      <div class="material-tabs">
        <button
          v-for="type in types"
          :key="type.label"
          :class="{ active: active === type.label }"
          @click="setType(type)"
        >
          {{ type.label }}
        </button>
      </div>

      <label class="dropzone">
        <input type="file" :accept="acceptedFiles" @change="choose" />
        <span class="cloud-icon"><AppIcon name="upload" /></span>
        <strong>点击或拖拽文件到这里上传</strong>
        <small>支持 {{ isPitch ? 'PPTX、PDF、DOC、DOCX、TXT' : 'PDF、DOC、DOCX、TXT' }}，单文件不超过 10MB</small>
      </label>

      <div v-if="file" class="uploaded-file">
        <span>■</span>
        <div>
          <strong>{{ file.name }}</strong>
          <small>{{ (file.size / 1024 / 1024).toFixed(2) }} MB</small>
          <i><b></b></i>
        </div>
        <em>100%</em>
        <span class="success">OK</span>
      </div>

      <section v-if="!isPitch" class="interview-mode-choice">
        <div><strong>选择面试模式</strong><span>上传完成后进入所选模式</span></div>
        <button :class="{ active: interviewExperience === 'text' }" @click="interviewExperience = 'text'">
          <b>文</b><span><strong>文本面试</strong><small>专注多轮文字问答</small></span>
        </button>
        <button :class="{ active: interviewExperience === 'avatar' }" @click="interviewExperience = 'avatar'">
          <b>人</b><span><strong>数字人面试</strong><small>数字人 + 真人摄像头</small></span>
        </button>
      </section>

      <p class="privacy-note">{{ status || `上传是可选项，也可以跳过材料直接进入${destinationLabel}。` }}</p>
      <p v-if="error" class="form-error">{{ error }}</p>

      <div class="page-actions">
        <button class="ghost-button" :disabled="preparing" @click="goInterview">
          {{ preparing ? '准备中...' : `跳过上传，进入${destinationLabel}` }}
        </button>
        <button class="primary-button next-button" :disabled="!file || preparing" @click="upload">
          上传并进入{{ destinationLabel }}<AppIcon name="arrow" />
        </button>
      </div>
    </section>
  </LayoutShell>
</template>

<style scoped>
.interview-mode-choice { display: grid; grid-template-columns: 1fr repeat(2, minmax(180px, .72fr)); align-items: stretch; gap: 12px; margin: 22px 0 8px; }
.interview-mode-choice > div { display: grid; align-content: center; gap: 5px; padding: 12px 4px; }.interview-mode-choice > div span { color: #8b98aa; font-size: 11px; }
.interview-mode-choice > button { display: flex; align-items: center; gap: 12px; border: 1px solid #dce4ef; border-radius: 11px; padding: 14px; color: #536079; background: #fff; text-align: left; }.interview-mode-choice > button.active { border-color: #3679df; box-shadow: 0 0 0 3px #edf4ff; color: #245fb7; background: #fbfdff; }.interview-mode-choice > button > b { display: grid; flex: 0 0 34px; height: 34px; place-items: center; border-radius: 9px; color: #fff; background: #6f8098; }.interview-mode-choice > button.active > b { background: #2d72d9; }.interview-mode-choice > button span { display: grid; gap: 4px; }.interview-mode-choice small { color: #93a0b1; font-size: 9px; }
@media(max-width:760px){.interview-mode-choice{grid-template-columns:1fr}.interview-mode-choice>div{padding-bottom:4px}}
</style>
