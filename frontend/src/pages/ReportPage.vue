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

const RADAR_CENTER = 150;
const RADAR_RADIUS = 91;
const radarLevels = [0.25, 0.5, 0.75, 1];

const dimensions = computed(() => Object.entries(report.value?.dimension_scores || {}).map(([label, value]) => ({
  label,
  value: Math.max(0, Math.min(100, Number(value) || 0))
})));

function polarPoint(index, total, radius) {
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / total;
  return {
    x: RADAR_CENTER + Math.cos(angle) * radius,
    y: RADAR_CENTER + Math.sin(angle) * radius
  };
}

function pointsToString(items) {
  return items.map((item) => `${item.x.toFixed(1)},${item.y.toFixed(1)}`).join(' ');
}

const radarGridPolygons = computed(() => radarLevels.map((level) => pointsToString(
  dimensions.value.map((_, index) => polarPoint(index, dimensions.value.length, RADAR_RADIUS * level))
)));

const radarAxes = computed(() => dimensions.value.map((_, index) => ({
  end: polarPoint(index, dimensions.value.length, RADAR_RADIUS)
})));

const radarValuePolygon = computed(() => pointsToString(dimensions.value.map((item, index) =>
  polarPoint(index, dimensions.value.length, RADAR_RADIUS * item.value / 100)
)));

const trendReports = computed(() => [...reports.value]
  .sort((left, right) => new Date(left.generated_at) - new Date(right.generated_at))
  .slice(-7));

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

function formatShortDate(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) : '';
}

function printReport() {
  window.print();
}

async function shareReport() {
  if (!report.value) return;
  try {
    if (navigator.share) {
      await navigator.share({
        title: `${reportTitle(report.value)}训练报告`,
        text: `CareerPilot AI 训练报告：${report.value.overall_score} 分`,
        url: window.location.href
      });
    } else {
      await navigator.clipboard.writeText(window.location.href);
      notice.value = '报告链接已复制';
    }
  } catch (err) {
    if (err?.name !== 'AbortError') error.value = '分享失败，请稍后重试';
  }
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
        <div>
          <button class="ghost-button" :disabled="!report" @click="printReport"><AppIcon name="download" />下载报告</button>
          <button class="ghost-button" :disabled="!report" @click="shareReport"><AppIcon name="share" />分享报告</button>
        </div>
      </header>

      <p v-if="loading" class="privacy-note">报告加载中...</p>
      <p v-if="notice" class="privacy-note">{{ notice }}</p>
      <p v-if="error" class="form-error">{{ error }}</p>

      <section v-if="reports.length" class="report-library history-library">
        <div class="report-library-head history-library-head">
          <div>
            <span class="history-eyebrow">REPORT HISTORY</span>
            <h2>历史报告</h2>
            <p>共 {{ reports.length }} 份独立报告，点击下方任意一份切换查看</p>
          </div>
          <span class="current-report-label">正在查看：<b>{{ reportTitle(report) }}</b></span>
        </div>
        <div class="report-list history-list">
          <button
            v-for="(item, index) in reports"
            :key="item.session_id"
            :class="{ active: report?.session_id === item.session_id }"
            @click="selectReport(item)"
          >
            <i>{{ String(index + 1).padStart(2, '0') }}</i>
            <span>{{ reportTitle(item) }}</span>
            <b>{{ item.overall_score }} 分</b>
            <small>{{ formatDate(item.generated_at) }}</small>
            <em v-if="report?.session_id === item.session_id">当前查看</em>
          </button>
        </div>
      </section>
      <p v-else-if="!loading" class="privacy-note">还没有已保存的报告，完成一次笔试或面试后即可生成。</p>

      <template v-if="report">
        <div class="report-top-grid">
          <article class="score-card"><span>综合得分</span><div><b>{{ report.overall_score }}</b><em>/100</em></div><p>{{ report.summary }}</p><i>已保存</i></article>
          <article class="analysis-card">
            <h2>能力维度分析</h2>
            <div v-if="dimensions.length >= 3" class="dimension-analysis">
              <div class="radar dynamic-radar">
                <svg viewBox="0 0 300 300" role="img" :aria-label="`${dimensions.length}项能力维度雷达图`">
                  <polygon v-for="(polygon, index) in radarGridPolygons" :key="index" :points="polygon" class="radar-grid" />
                  <line v-for="(axis, index) in radarAxes" :key="`axis-${index}`" :x1="RADAR_CENTER" :y1="RADAR_CENTER" :x2="axis.end.x" :y2="axis.end.y" class="radar-axis" />
                  <polygon :points="radarValuePolygon" class="radar-value" />
                  <circle
                    v-for="(item, index) in dimensions"
                    :key="`point-${item.label}`"
                    :cx="polarPoint(index, dimensions.length, RADAR_RADIUS * item.value / 100).x"
                    :cy="polarPoint(index, dimensions.length, RADAR_RADIUS * item.value / 100).y"
                    r="4"
                    class="radar-dot"
                  />
                </svg>
              </div>
              <div class="radar-legend" aria-label="能力维度分数">
                <div v-for="item in dimensions" :key="item.label">
                  <span>{{ item.label }}</span><b>{{ item.value }}</b>
                </div>
              </div>
            </div>
            <p v-else class="radar-empty">维度数据不足</p>
          </article>
          <article class="trend-card">
            <h2>得分趋势</h2>
            <div class="chart real-chart">
              <i v-for="item in trendReports" :key="item.session_id" :style="{ height: `${item.overall_score}%` }">
                <span>{{ item.overall_score }}</span><b></b>
              </i>
            </div>
            <div class="chart-labels">
              <span>{{ formatShortDate(trendReports[0]?.generated_at) }}</span>
              <span>最近 {{ trendReports.length }} 份</span>
              <span>{{ formatShortDate(trendReports.at(-1)?.generated_at) }}</span>
            </div>
          </article>
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

<style scoped>
.history-library { border: 1px solid #cbdcf5; border-left: 4px solid #2c70d7; padding: 20px; background: linear-gradient(100deg,#f8fbff,#fff 55%); box-shadow: 0 8px 24px rgba(36,76,139,.07); }
.history-library-head { align-items: flex-end; }
.history-library-head > div { display: grid; gap: 4px; }
.history-library-head h2 { margin: 0; color: #263950; font-size: 19px; }
.history-library-head p { margin: 1px 0 0; color: #728198; font-size: 12px; }
.history-eyebrow { color: #2b6fd2!important; font-size: 9px!important; font-weight: 900; letter-spacing: 1.8px; }
.current-report-label { border-radius: 99px; padding: 9px 13px; color: #5e6f87!important; background: #eaf2ff; font-size: 11px!important; }
.current-report-label b { color: #2364c8; }
.history-list { grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; }
.history-list button { position: relative; grid-template-columns: 40px minmax(0,1fr) auto; grid-template-rows: auto auto; align-items: center; gap: 7px 12px; min-height: 96px; padding: 16px; }
.history-list button > i { grid-row: 1/3; display: grid; width: 36px; height: 36px; place-items: center; border-radius: 9px; color: #60789d; background: #eaf0f8; font-family: Georgia,serif; font-size: 11px; font-style: normal; }
.history-list button > span { grid-column: 2; font-size: 14px; }
.history-list button > b { grid-column: 3; grid-row: 1/3; align-self: center; font-size: 19px; }
.history-list button > small { grid-column: 2; margin: 0; color: #8794a8; font-size: 11px; }
.history-list button > em { position: absolute; right: 10px; top: 8px; border-radius: 99px; padding: 4px 8px; color: #fff; background: #2c70d7; font-size: 9px; font-style: normal; }
.history-list button.active > i { color: #fff; background: #2c70d7; }
.history-list button.active > b { padding-top: 19px; }
.report-top-grid { grid-template-columns: 250px minmax(390px,1.3fr) minmax(280px,1fr); }
.analysis-card { min-height: 245px; overflow: visible; }
.dimension-analysis { display: grid; grid-template-columns: minmax(205px,1fr) minmax(130px,.72fr); align-items: center; gap: 14px; margin-top: 6px; }
.dynamic-radar { width: 100%; height: 205px; margin: 0; }
.dynamic-radar:before,.dynamic-radar:after { display: none; content: none; }
.dynamic-radar svg { width: 100%; height: 100%; overflow: visible; }
.radar-grid { fill: rgba(235,242,252,.28); stroke: #dce5f2; stroke-width: 1; }
.radar-axis { stroke: #e2e9f2; stroke-width: 1; }
.radar-value { fill: rgba(51,119,224,.25); stroke: #3476dd; stroke-width: 2; stroke-linejoin: round; }
.radar-dot { fill: #fff; stroke: #286bd2; stroke-width: 2; }
.radar-legend { display: grid; gap: 7px; }
.radar-legend > div { display: flex; min-height: 24px; align-items: center; justify-content: space-between; gap: 10px; border-bottom: 1px solid #edf1f6; padding: 3px 1px 6px; }
.radar-legend span { color: #4e5f77; font-size: 12px; font-weight: 600; white-space: nowrap; }
.radar-legend b { color: #2465c6; font-family: Georgia,serif; font-size: 15px; }
.radar-empty { display: grid; height: 160px; place-items: center; color: #929dad; font-size: 10px; }
.real-chart i { min-height: 2px; border-top-color: #3475db; background: linear-gradient(to top,rgba(66,128,222,.04),rgba(66,128,222,.14)); }
.real-chart i > span { position: absolute; left: 50%; top: -18px; color: #3971c6; font-size: 8px; transform: translateX(-50%); }
@media(max-width:1100px){.report-top-grid{grid-template-columns:1fr 1fr}.trend-card{grid-column:1/-1}.history-list{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:760px){.report-top-grid{grid-template-columns:1fr}.trend-card{grid-column:auto}.history-library-head{align-items:flex-start;flex-direction:column}.current-report-label{margin-top:12px}.history-list{grid-template-columns:1fr}.history-list button{grid-template-columns:40px minmax(0,1fr) auto}}
@media(max-width:480px){.dimension-analysis{grid-template-columns:1fr}.dynamic-radar{height:220px}.radar-legend{grid-template-columns:1fr 1fr}}
@media print{.sidebar,.report-library,.report-header>div:last-child{display:none!important}.app-shell{display:block}.report-page{max-width:none;padding:0}}
</style>
