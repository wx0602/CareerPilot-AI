<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import { api, setSession } from '../api/client';

const router = useRouter();
const loading = ref('');
const error = ref('');

const scenarios = [
  {
    icon: '▣',
    tone: 'blue',
    mode: 'technical',
    title: '企业笔试',
    desc: '真题训练 · 智能评估',
    note: '适合技术类岗位',
    route: '/study-plan'
  },
  {
    icon: '◎',
    tone: 'green',
    mode: 'job',
    title: '文本面试',
    desc: 'AI 模拟面试 · 实时对话',
    note: '适合各类岗位',
    route: '/upload'
  },
  {
    icon: '◍',
    tone: 'purple',
    mode: 'job',
    title: '群体面试',
    desc: '多人协作 · 角色扮演',
    note: '适合管理类岗位',
    route: '/interview'
  },
  {
    icon: '◌',
    tone: 'violet',
    mode: 'job',
    title: '压力面试',
    desc: '高强问答 · 抗压训练',
    note: '适合高强度岗位',
    route: '/interview'
  },
  {
    icon: '☆',
    tone: 'orange',
    mode: 'pitch',
    title: '路演答辩',
    desc: '商业逻辑 · 投资人追问',
    note: '适合创业项目',
    route: '/interview'
  },
  {
    icon: '◈',
    tone: 'indigo',
    mode: 'job',
    title: '职业规划',
    desc: '职业发展 · 方向探索',
    note: '适合求职规划',
    route: '/career-assessment',
    requiresSession: false
  }
];

async function start(item) {
  if (item.requiresSession === false) {
    router.push(item.route);
    return;
  }
  loading.value = item.title;
  error.value = '';
  try {
    const session = await api.createSession({
      mode: item.mode,
      position: item.mode === 'technical' ? '软件工程师' : null,
      company: 'CareerPilot 练习题库'
    });
    setSession(session);
    router.push(item.route);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = '';
  }
}
</script>

<template>
  <LayoutShell>
    <section class="page dashboard-page">
      <header class="dashboard-header">
        <div>
          <h1>选择训练场景</h1>
          <p>首页只做场景选择。企业笔试进入学习计划后再选学习模块。</p>
        </div>
        <div class="practice-summary">当前首页保持场景入口</div>
        <div class="user-avatar">AI</div>
      </header>

      <p v-if="error" class="form-error">{{ error }}</p>

      <div class="scenario-grid">
        <article v-for="item in scenarios" :key="item.title" class="scenario-card">
          <span class="scenario-icon" :class="item.tone">{{ item.icon }}</span>
          <h2>{{ item.title }}</h2>
          <p>{{ item.desc }}</p>
          <small>{{ item.note }}</small>
          <button class="outline-button" :disabled="!!loading" @click="start(item)">
            {{ loading === item.title ? '创建中...' : '开始训练' }}
          </button>
        </article>
      </div>
    </section>
  </LayoutShell>
</template>
