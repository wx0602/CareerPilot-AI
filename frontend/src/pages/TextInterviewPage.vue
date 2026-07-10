<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandLogo from '../components/BrandLogo.vue';

const router = useRouter();
const text = ref('');
const messages = ref([
  { role: 'ai', text: '请你介绍一下你在最近一个项目中承担的角色，以及你是如何解决代码规范问题的？', time: '10:15' },
  { role: 'user', text: '我在项目中负责后端框架设计与开发，主要使用了 Spring Boot 和 MySQL。', time: '10:16' },
  { role: 'ai', text: '能否具体说一下，当时的团队是如何协作的？你是如何分析和解决冲突的？', time: '10:16' }
]);
function send() { if (!text.value.trim()) return; messages.value.push({ role: 'user', text: text.value, time: '现在' }); text.value = ''; }
</script>

<template>
  <main class="interview-page">
    <header class="interview-topbar"><BrandLogo /><button class="back-link" @click="router.push('/dashboard')"><AppIcon name="back" />返回</button><h1>模拟面试 · 软件工程师</h1><span>面试时长 12:45</span><button class="outline-button" @click="router.push('/report')">结束面试</button></header>
    <div class="interview-layout">
      <aside class="progress-panel"><h2>面试进度</h2><ol><li class="done">自我介绍</li><li class="done">项目经验</li><li class="active">技术能力</li><li>问题解决</li><li>职业规划</li><li>反问环节</li></ol></aside>
      <section class="chat-panel">
        <div class="messages">
          <article v-for="(message, i) in messages" :key="i" :class="['message', message.role]">
            <div class="message-avatar">{{ message.role === 'ai' ? 'AI' : '我' }}</div>
            <div><b>{{ message.role === 'ai' ? '面试官（AI）' : '你' }}</b><p>{{ message.text }}</p><time>{{ message.time }}</time></div>
          </article>
          <div class="typing"><i></i><i></i><i></i></div>
        </div>
        <form class="chat-composer" @submit.prevent="send"><textarea v-model="text" placeholder="输入你的回答...&#10;按 Enter 发送，Shift + Enter 换行" @keydown.enter.exact.prevent="send"></textarea><button type="submit">➤</button></form>
      </section>
    </div>
  </main>
</template>
