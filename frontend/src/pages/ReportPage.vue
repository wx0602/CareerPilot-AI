<script setup>
import { computed, onMounted, ref } from 'vue';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, getSession } from '../api/client';

const reports = ref([]);
const report = ref(null);
const error = ref('');
const notice = ref('');
const loading = ref(false);
const points = computed(() => Object.entries(report.value?.dimension_scores || {}));

onMounted(loadReports);

function selectReport(item) {
  report.value = item;
}

function reportTitle(item) {
  return item.learning_module_title || item.position || '综合训练';
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '';
}

async function loadReports() {
  const session = getSession();
  let generationError = '';
  loading.value = true;
  error.value = '';
  notice.value = '';
  try {
    if (session) {
      try {
        await api.generateReport({ session_id: session.session_id });
        notice.value = '当前训练报告已自动保存';
      } catch (err) {
        if (!err.message.includes('至少完成')) generationError = err.message;
      }
    }
    reports.value = await api.listReports();
    report.value =
      reports.value.find((item) => item.session_id === session?.session_id) ||
      reports.value[0] ||
      null;
    error.value = generationError;
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
        <div>
          <button class="back-link" @click="$router.push('/dashboard')"><AppIcon name="back" />返回</button>
          <h1>我的报告</h1>
          <p>训练结束后自动保存，可随时查看历史报告</p>
        </div>
        <div><button class="ghost-button"><AppIcon name="download" />下载报告</button><button class="ghost-button"><AppIcon name="share" />分享报告</button></div>
      </header>

      <p v-if="loading" class="privacy-note">报告加载中...</p>
      <p v-if="notice" class="privacy-note">{{ notice }}</p>
      <p v-if="error" class="form-error">{{ error }}</p>

      <section v-if="reports.length" class="report-library">
        <div class="report-library-head"><h2>已保存报告</h2><span>{{ reports.length }} 份</span></div>
        <div class="report-list">
          <button
            v-for="item in reports"
            :key="item.session_id"
            :class="{ active: report?.session_id === item.session_id }"
            @click="selectReport(item)"
          >
            <span>{{ reportTitle(item) }}</span>
            <b>{{ item.overall_score }} 分</b>
            <small>{{ formatDate(item.generated_at) }}</small>
          </button>
        </div>
      </section>
      <p v-else-if="!loading" class="privacy-note">还没有已保存的报告，完成一次笔试或面试后即可生成。</p>

      <template v-if="report">
        <div class="report-top-grid">
          <article class="score-card"><span>综合得分</span><div><b>{{ report.overall_score }}</b><em>/100</em></div><p>{{ report.summary }}</p><i>已保存</i></article>
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
