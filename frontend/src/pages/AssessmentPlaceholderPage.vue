<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import LayoutShell from '../components/LayoutShell.vue';
import { getCareerAssessment } from '../data/careerAssessments';

const route = useRoute();
const assessment = computed(() => getCareerAssessment(route.params.assessmentId));
</script>

<template>
  <LayoutShell>
    <section class="page assessment-placeholder-page">
      <RouterLink class="back-link" to="/career-assessment"><AppIcon name="back" />返回测评选择</RouterLink>
      <div v-if="assessment" class="assessment-placeholder-card">
        <span>{{ assessment.code }}</span>
        <h1>{{ assessment.title }}</h1>
        <p>{{ assessment.description }}</p>
        <div>
          <b>测试题目待接入</b>
          <small>后续可在此处加入题目、选项、进度条和提交计分逻辑。</small>
        </div>
        <RouterLink class="primary-button" to="/career-assessment">选择其他测评</RouterLink>
      </div>
      <div v-else class="assessment-placeholder-card">
        <h1>未找到该测评</h1>
        <RouterLink class="primary-button" to="/career-assessment">返回测评列表</RouterLink>
      </div>
    </section>
  </LayoutShell>
</template>
