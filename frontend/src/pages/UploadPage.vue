<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, getSession } from '../api/client';
import { QUESTION_MIX_LABEL } from '../data/learningModules';

const router = useRouter();
const materialType = ref('resume');
const active = ref('简历');
const file = ref(null);
const status = ref('');
const error = ref('');
const session = ref(getSession());

const moduleTitle = computed(() => session.value?.learning_module_title || '未选择模块');

const types = [
  { label: '简历', value: 'resume' },
  { label: '职位描述（JD）', value: 'jd' },
  { label: '项目资料', value: 'resume' },
  { label: '其他材料', value: 'resume' }
];

function setType(type) {
  active.value = type.label;
  materialType.value = type.value;
}

function choose(event) {
  file.value = event.target.files?.[0] || null;
  status.value = '';
  error.value = '';
}

async function upload() {
  if (!session.value) {
    router.push('/dashboard');
    return;
  }
  if (!session.value.learning_module) {
    router.push('/study-plan');
    return;
  }
  if (!file.value) return;
  status.value = '上传解析中...';
  error.value = '';
  try {
    const result = await api.uploadMaterial({
      sessionId: session.value.session_id,
      materialType: materialType.value,
      file: file.value
    });
    status.value = `解析状态：${result.parse_status}`;
  } catch (err) {
    error.value = err.message;
    status.value = '';
  }
}

function goExam() {
  if (!session.value?.learning_module) {
    router.push('/study-plan');
    return;
  }
  router.push('/exam');
}
</script>

<template>
  <LayoutShell>
    <section class="page upload-page">
      <header>
        <h1>上传练习材料</h1>
        <p>当前模块为 {{ moduleTitle }}，笔试将按 {{ QUESTION_MIX_LABEL }} 的固定配比生成。</p>
      </header>

      <div class="upload-summary">
        <span>学习模块</span>
        <b>{{ moduleTitle }}</b>
        <small>{{ QUESTION_MIX_LABEL }}</small>
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

      <p class="privacy-note">{{ status || '上传是可选项，也可以直接进入笔试。' }}</p>
      <p v-if="error" class="form-error">{{ error }}</p>

      <div class="page-actions">
        <button class="ghost-button" @click="goExam">跳过上传，进入笔试</button>
        <button class="primary-button next-button" :disabled="!file" @click="upload">上传材料</button>
        <button class="primary-button next-button" @click="goExam">
          进入笔试<AppIcon name="arrow" />
        </button>
      </div>
    </section>
  </LayoutShell>
</template>
