<script setup>
import LayoutShell from '../components/LayoutShell.vue';
import { scenarios } from '../data/mockData';
</script>

<template>
  <LayoutShell>
    <section class="page dashboard-page">
      <header class="dashboard-header">
        <div><h1>选择练习场景</h1><p>选择你想要练习的场景，开启针对性训练</p></div>
        <div class="practice-summary">◉ 今日练习 <b>0</b> 分钟</div>
        <div class="user-avatar">恒</div>
      </header>
      <div class="scenario-grid">
        <article v-for="item in scenarios" :key="item.title" class="scenario-card">
          <span class="scenario-icon" :class="item.tone">{{ item.icon }}</span>
          <h2>{{ item.title }}</h2><p>{{ item.desc }}</p><small>{{ item.note }}</small>
          <RouterLink v-if="item.ready" :to="item.route" class="outline-button">开始练习</RouterLink>
          <button v-else class="outline-button disabled" disabled>即将上线</button>
        </article>
      </div>
    </section>
  </LayoutShell>
</template>
