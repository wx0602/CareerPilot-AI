<script setup>
import AppIcon from '../components/AppIcon.vue';
import LayoutShell from '../components/LayoutShell.vue';
import { careerAssessments } from '../data/careerAssessments';
</script>

<template>
  <LayoutShell>
    <section class="page career-assessment-page">
      <header class="career-assessment-header">
        <div>
          <p class="career-kicker">CAREER DISCOVERY</p>
          <h1>职业规划</h1>
          <p>选择一项测评，认识你的兴趣、性格与职业驱动力。</p>
        </div>
        <div class="assessment-progress"><b>4</b><span>项基础测评</span></div>
      </header>

      <div class="assessment-note">
        <strong>从了解自己开始</strong>
        <p>将打开第三方中文测评；基础结果免费，部分平台可能提供可选的付费进阶服务。</p>
      </div>

      <div class="assessment-grid">
        <article
          v-for="(item, index) in careerAssessments"
          :key="item.id"
          class="assessment-card"
          :class="item.tone"
        >
          <div class="assessment-card-top">
            <span class="assessment-number">0{{ index + 1 }}</span>
            <span class="assessment-code">{{ item.code }}</span>
          </div>
          <h2>{{ item.title }}</h2>
          <p>{{ item.description }}</p>
          <div class="assessment-card-footer">
            <div class="assessment-card-meta">
              <small>{{ item.meta }}</small>
              <small>{{ item.provider }} · {{ item.freeLabel }}</small>
            </div>
            <a
              :href="item.externalUrl"
              target="_blank"
              rel="noopener noreferrer"
              :aria-label="`在新标签页打开${item.title}`"
            >
              开始测试<AppIcon name="arrow" />
            </a>
          </div>
        </article>
      </div>
    </section>
  </LayoutShell>
</template>

<style scoped>
.assessment-card-meta {
  display: grid;
  gap: 5px;
}

.assessment-card-meta small:last-child {
  color: #718097;
}
</style>
