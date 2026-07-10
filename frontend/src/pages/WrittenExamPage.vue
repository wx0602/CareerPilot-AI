<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandLogo from '../components/BrandLogo.vue';
import { questions } from '../data/mockData';

const router = useRouter();
const current = ref(0);
const answers = ref({ 1: 1 });
const question = computed(() => questions[current.value]);
function next() { if (current.value < questions.length - 1) current.value++; else router.push('/report'); }
</script>

<template>
  <main class="exam-page">
    <header class="exam-topbar"><BrandLogo /><button class="back-link" @click="router.push('/dashboard')"><AppIcon name="back" />返回</button><h1>字节跳动 · 后端开发工程师笔试</h1><span class="timer"><AppIcon name="clock" />剩余时间 01:28:36</span><button class="primary-button submit-small" @click="router.push('/report')">交卷</button></header>
    <div class="exam-layout">
      <aside class="question-nav">
        <h2>题目列表</h2>
        <section><b>单选题 ({{ questions.length }})</b><div><button v-for="(q, i) in questions" :key="q.id" :class="{ active: current === i, done: answers[q.id] !== undefined }" @click="current = i">{{ q.id }}</button></div></section>
        <section><b>多选题 (10)</b><div><button v-for="n in 10" :key="n">{{ n }}</button></div></section>
        <section><b>编程题 (2)</b><div><button>1</button><button>2</button></div></section>
      </aside>
      <section class="question-panel">
        <div class="question-meta"><b>单选题 {{ current + 1 }}/{{ questions.length }}</b><span>每题 2 分</span></div>
        <h2>{{ question.stem }}</h2>
        <label v-for="(option, i) in question.options" :key="option" class="option-row" :class="{ selected: answers[question.id] === i }">
          <input v-model="answers[question.id]" type="radio" :value="i" /><b>{{ String.fromCharCode(65 + i) }}.</b><span>{{ option }}</span>
        </label>
        <div class="question-actions"><button class="ghost-button">☆ 标记</button><span></span><button class="ghost-button" :disabled="current === 0" @click="current--">上一题</button><button class="primary-button" @click="next">{{ current === questions.length - 1 ? '完成考试' : '下一题' }}</button></div>
      </section>
    </div>
  </main>
</template>
