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
    route: '/scene/written'
  },
  {
    icon: '◎',
    tone: 'green',
    mode: 'job',
    title: '文本面试',
    desc: 'AI 模拟面试 · 实时对话',
    note: '适合各类岗位',
    route: '/scene/text-interview'
  },
  {
    icon: '◍',
    tone: 'purple',
    mode: 'group_interview',
    title: '群体面试',
    desc: '多人协作 · 角色扮演',
    note: '适合管理类岗位',
    route: '/scene/group'
  },
  {
    icon: '◌',
    tone: 'coral',
    mode: 'stress_interview',
    title: '压力面试',
    desc: '高强问答 · 抗压训练',
    note: '适合高强度岗位',
    route: '/scene/stress'
  },
  {
    icon: '☆',
    tone: 'orange',
    mode: 'pitch',
    title: '路演答辩',
    desc: '商业逻辑 · 投资人追问',
    note: '适合创业项目',
    route: '/scene/pitch'
  },
  {
    icon: '◈',
    tone: 'indigo',
    mode: 'job',
    title: '职业规划',
    desc: '职业发展 · 方向探索',
    note: '适合求职规划',
    route: '/scene/career',
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
      position: null,
      company: null
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
          <p>首页只做场景选择。企业笔试进入后再选择目标企业与应聘岗位。</p>
        </div>
        <div class="practice-summary">当前首页保持场景入口</div>
        <div class="user-avatar">AI</div>
      </header>

      <p v-if="error" class="form-error">{{ error }}</p>

      <div class="scenario-grid">
        <article v-for="item in scenarios" :key="item.title" :class="['scenario-card', `tone-${item.tone}`]">
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

<style scoped>
.scenario-card {
  --scene-color: #2d6ed2;
  --scene-soft: #eaf2ff;
  --scene-border: #cdddf5;
  position: relative;
  overflow: hidden;
  border-color: var(--scene-border);
  background: linear-gradient(145deg, #fff 55%, var(--scene-soft));
}
.scenario-card:after {
  content: '';
  position: absolute;
  right: -46px;
  top: -54px;
  width: 145px;
  height: 145px;
  border: 24px solid var(--scene-color);
  border-radius: 50%;
  opacity: .055;
  pointer-events: none;
}
.scenario-card.tone-blue { --scene-color: #2d6ed2; --scene-soft: #eaf2ff; --scene-border: #cfdef5; }
.scenario-card.tone-green { --scene-color: #238367; --scene-soft: #e5f4ee; --scene-border: #cce6dc; }
.scenario-card.tone-purple { --scene-color: #7b4eae; --scene-soft: #f0e8f7; --scene-border: #dfd0ed; }
.scenario-card.tone-coral { --scene-color: #bd554e; --scene-soft: #fae9e6; --scene-border: #efcfca; }
.scenario-card.tone-orange { --scene-color: #b96829; --scene-soft: #f9eddc; --scene-border: #ead7bc; }
.scenario-card.tone-indigo { --scene-color: #4358a8; --scene-soft: #e8ebf8; --scene-border: #d1d7ef; }
.scenario-card .scenario-icon { color: #fff; background: var(--scene-color); box-shadow: 0 8px 20px color-mix(in srgb, var(--scene-color) 24%, transparent); }
.scenario-card h2 { color: color-mix(in srgb, var(--scene-color) 72%, #17243a); }
.scenario-card .outline-button { border-color: var(--scene-border); color: var(--scene-color); background: rgba(255,255,255,.82); }
.scenario-card .outline-button:hover { color: #fff; background: var(--scene-color); }
</style>
