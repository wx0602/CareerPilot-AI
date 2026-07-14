<script setup>
import { computed, onMounted, ref } from 'vue';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, getSession } from '../api/client';

const report = ref(null);
const error = ref('');
const loading = ref(false);
const points = computed(() => Object.entries(report.value?.dimension_scores || {}));

onMounted(loadReport);

async function loadReport() {
  const session = getSession();
  if (!session) return;
  loading.value = true;
  try {
    report.value = await api.generateReport({ session_id: session.session_id });
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <LayoutShell>
    <section class="page report-page">
      <header class="report-header">
        <div><button class="back-link" @click="$router.push('/dashboard')"><AppIcon name="back" />返回</button><h1>综合评估报告</h1><p>由真实训练结果生成</p></div><div><button class="ghost-button"><AppIcon name="download" />下载报告</button><button class="ghost-button"><AppIcon name="share" />分享报告</button></div>
      </header>
      <p v-if="loading" class="privacy-note">报告生成中...</p>
      <p v-if="error" class="form-error">{{ error }}</p>
      <template v-if="report">
        <div class="report-top-grid">
          <article class="score-card"><span>综合得分</span><div><b>{{ report.overall_score }}</b><em>/100</em></div><p>{{ report.summary }}</p><i>实时</i></article>
          <article class="analysis-card"><h2>能力维度分析</h2><div class="radar"><span v-for="(item, i) in points" :key="item[0]" :style="{ transform: `rotate(${i * 72}deg) translateY(-72px) rotate(${-i * 72}deg)` }">{{ item[0] }}<b>{{ item[1] }}</b></span><div class="radar-shape"></div></div></article>
          <article class="trend-card"><h2>得分趋势</h2><div class="chart"><i v-for="(h, i) in [30,48,62,45,66,72,report.overall_score]" :key="i" :style="{ height: h + '%' }"><b></b></i></div><div class="chart-labels"><span>笔试</span><span>面试</span><span>报告</span></div></article>
        </div>
        <div class="report-bottom-grid">
          <article class="insight-card strengths"><h2>♙ 优势亮点</h2><ul><li v-for="item in report.strengths" :key="item">{{ item }}</li></ul></article>
          <article class="insight-card weaknesses"><h2>※ 待提升项</h2><ul><li v-for="item in report.weaknesses" :key="item">{{ item }}</li></ul></article>
          <article class="insight-card suggestions"><h2>⊙ AI 建议</h2><p v-for="item in report.suggestions" :key="item">{{ item }}</p></article>
        </div>
      </template>
    </section>
  </LayoutShell>
</template>
