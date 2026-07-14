<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandLogo from '../components/BrandLogo.vue';
import { api, getSession } from '../api/client';

const router = useRouter();
const text = ref('');
const messages = ref([]);
const currentQuestion = ref(null);
const loading = ref(false);
const error = ref('');
const session = ref(null);

const interviewTitle = computed(
  () => session.value?.learning_module_title || session.value?.position || '模拟面试'
);

onMounted(async () => {
  session.value = getSession();
  await loadFirstQuestion();
});

async function loadFirstQuestion() {
  if (!session.value) {
    router.push('/dashboard');
    return;
  }
  loading.value = true;
  try {
    const data = await api.interviewMessage({ session_id: session.value.session_id });
    currentQuestion.value = data.next_question;
    messages.value.push({ role: 'ai', text: data.next_question.question });
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function send() {
  if (!session.value || !currentQuestion.value || !text.value.trim()) return;
  const answer = text.value.trim();
  messages.value.push({ role: 'user', text: answer });
  text.value = '';
  loading.value = true;
  error.value = '';
  try {
    const data = await api.interviewMessage({
      session_id: session.value.session_id,
      question_id: currentQuestion.value.question_id,
      answer
    });
    if (data.evaluation) {
      const strengths = data.evaluation.strengths.join('、') || '暂无';
      const weaknesses = data.evaluation.weaknesses.join('、') || '暂无';
      messages.value.push({
        role: 'ai',
        text: `本轮评分 ${data.evaluation.score} 分。优点：${strengths}。不足：${weaknesses}。`
      });
    }
    currentQuestion.value = data.next_question;
    messages.value.push({ role: 'ai', text: data.next_question.question });
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function finishInterview() {
  if (!session.value || loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    await api.generateReport({ session_id: session.value.session_id });
    await router.push('/report');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="interview-page">
    <header class="interview-topbar">
      <BrandLogo />
      <button class="back-link" @click="router.push('/dashboard')">
        <AppIcon name="back" />返回
      </button>
      <h1>模拟面试 · {{ interviewTitle }}</h1>
      <span>训练中</span>
      <button class="outline-button" :disabled="loading" @click="finishInterview">结束面试并保存报告</button>
    </header>

    <p v-if="error" class="form-error">{{ error }}</p>

    <div class="interview-layout">
      <aside class="progress-panel">
        <h2>面试进度</h2>
        <ol>
          <li class="done">基础热身</li>
          <li class="done">项目经历</li>
          <li class="active">核心能力</li>
          <li>问题解决</li>
          <li>职业规划</li>
          <li>复盘总结</li>
        </ol>
      </aside>

      <section class="chat-panel">
        <div class="messages">
          <article v-for="(message, i) in messages" :key="i" :class="['message', message.role]">
            <div class="message-avatar">{{ message.role === 'ai' ? 'AI' : '我' }}</div>
            <div>
              <b>{{ message.role === 'ai' ? '面试官（AI）' : '我' }}</b>
              <p>{{ message.text }}</p>
              <time>{{ message.time || '现在' }}</time>
            </div>
          </article>
          <div v-if="loading" class="typing"><i></i><i></i><i></i></div>
        </div>

        <form class="chat-composer" @submit.prevent="send">
          <textarea
            v-model="text"
            placeholder="输入你的回答..."
            @keydown.enter.exact.prevent="send"
          ></textarea>
          <button type="submit" :disabled="loading">→</button>
        </form>
      </section>
    </div>
  </main>
</template>
