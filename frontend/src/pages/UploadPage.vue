<script setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, getSession, setSession } from '../api/client';

const router = useRouter();
const route = useRoute();
const materialType = ref('resume');
const active = ref('简历');
const file = ref(null);
const status = ref('');
const error = ref('');
const session = ref(getSession());
const preparing = ref(false);

const types = [
  { label: '简历', value: 'resume' },
  { label: '职位描述（JD）', value: 'jd' }
];

onMounted(async () => {
  if (route.query.new === '1') {
    await ensureInterviewSession(true);
    await router.replace('/upload');
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
  if (session.value && !forceNew) return session.value;
  preparing.value = true;
  error.value = '';
  try {
    const created = await api.createSession({
      mode: 'job',
      position: '目标岗位',
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
      await router.push('/interview');
    }
  } catch (err) {
    error.value = err.message;
    status.value = '';
  }
}

async function goInterview() {
  const currentSession = await ensureInterviewSession();
  if (currentSession) await router.push('/interview');
}
</script>

<template>
  <LayoutShell>
    <section class="page upload-page">
      <header>
        <h1>上传简历</h1>
        <p>上传简历或职位描述后，AI 面试官会结合材料进行针对性提问。</p>
      </header>

      <div class="upload-summary">
        <span>训练流程</span>
        <b>材料解析 → 模拟面试 → 自动生成报告</b>
        <small>简历材料只用于面试，不参与企业笔试组卷。</small>
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
        <input type="file" accept=".pdf,.doc,.docx,.txt" @change="choose" />
        <span class="cloud-icon"><AppIcon name="upload" /></span>
        <strong>点击或拖拽文件到这里上传</strong>
        <small>支持 PDF、DOC、DOCX、TXT，单文件不超过 10MB</small>
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

      <p class="privacy-note">{{ status || '上传是可选项，也可以跳过材料直接进入面试。' }}</p>
      <p v-if="error" class="form-error">{{ error }}</p>

      <div class="page-actions">
        <button class="ghost-button" :disabled="preparing" @click="goInterview">
          {{ preparing ? '准备中...' : '跳过上传，进入面试' }}
        </button>
        <button class="primary-button next-button" :disabled="!file || preparing" @click="upload">
          上传并进入面试<AppIcon name="arrow" />
        </button>
      </div>
    </section>
  </LayoutShell>
</template>
