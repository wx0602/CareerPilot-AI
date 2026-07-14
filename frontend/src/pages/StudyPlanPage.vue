<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import { api, getSession, setSession } from '../api/client';
import { QUESTION_MIX, QUESTION_MIX_LABEL, learningModules } from '../data/learningModules';

const router = useRouter();
const session = ref(getSession());
const loading = ref(false);
const error = ref('');
const selectedModuleId = ref(session.value?.learning_module || 'java_backend');

const selectedModule = computed(
  () => learningModules.find((item) => item.id === selectedModuleId.value) || null
);

function selectModule(item) {
  selectedModuleId.value = item.id;
  error.value = item.available ? '' : `${item.title} 模块题库待补充，当前先保留入口。`;
}

async function confirmAndNext() {
  if (!session.value) {
    router.push('/dashboard');
    return;
  }
  const module = selectedModule.value;
  if (!module || !module.available) {
    error.value = '请选择一个已可用的学习模块。';
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    const updated = await api.updateSession(session.value.session_id, {
      position: module.position,
      learning_module: module.id,
      learning_module_title: module.title,
      question_mix: QUESTION_MIX
    });
    setSession(updated);
    session.value = updated;
    router.push('/upload');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <LayoutShell>
    <section class="page dashboard-page">
      <header class="dashboard-header">
        <div>
          <h1>学习计划</h1>
          <p>在这里选择学习模块。技术类笔试会按固定配比出题。</p>
        </div>
        <div class="practice-summary">当前配比 <b>{{ QUESTION_MIX_LABEL }}</b></div>
      </header>

      <section class="module-section">
        <div class="module-section-head">
          <div>
            <h2>学习模块选择</h2>
            <p>Java 和 Python 已可直接使用；前端、Go、C++、AI、产品、测试、运维先预留模块入口。</p>
          </div>
          <div class="module-chip">{{ selectedModule?.title || '未选择模块' }}</div>
        </div>

        <div class="module-grid">
          <button
            v-for="item in learningModules"
            :key="item.id"
            class="module-card"
            :class="{ active: selectedModuleId === item.id, locked: !item.available }"
            @click="selectModule(item)"
          >
            <span class="module-tag">{{ item.category }}</span>
            <strong>{{ item.title }}</strong>
            <p>{{ item.summary }}</p>
            <small>{{ item.available ? '已接入题库' : '待补真实题库' }}</small>
          </button>
        </div>
      </section>

      <p v-if="error" class="form-error">{{ error }}</p>

      <div class="page-actions plan-actions">
        <button class="ghost-button" @click="router.push('/dashboard')">返回场景选择</button>
        <button class="primary-button next-button" :disabled="loading" @click="confirmAndNext">
          {{ loading ? '保存中...' : '保存模块并继续' }}
        </button>
      </div>
    </section>
  </LayoutShell>
</template>
