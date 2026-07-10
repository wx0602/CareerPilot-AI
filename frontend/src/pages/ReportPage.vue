<script setup>
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { report } from '../data/mockData';
const points = Object.entries(report.dimension_scores);
</script>

<template>
  <LayoutShell>
    <section class="page report-page">
      <header class="report-header"><div><button class="back-link" @click="$router.push('/dashboard')"><AppIcon name="back" />返回</button><h1>综合评估报告</h1><p>生成时间：2026-07-09 14:30</p></div><div><button class="ghost-button"><AppIcon name="download" />下载报告</button><button class="ghost-button"><AppIcon name="share" />分享报告</button></div></header>
      <div class="report-top-grid">
        <article class="score-card"><span>综合得分</span><div><b>{{ report.overall_score }}</b><em>/100</em></div><p>超过了 86% 的求职者</p><i>优秀</i></article>
        <article class="analysis-card"><h2>能力维度分析</h2><div class="radar"><span v-for="(item, i) in points" :key="item[0]" :style="{ transform: `rotate(${i * 72}deg) translateY(-72px) rotate(${-i * 72}deg)` }">{{ item[0] }}<b>{{ item[1] }}</b></span><div class="radar-shape"></div></div></article>
        <article class="trend-card"><h2>得分趋势</h2><div class="chart"><i v-for="(h, i) in [30,48,62,45,66,72,93]" :key="i" :style="{ height: h + '%' }"><b></b></i></div><div class="chart-labels"><span>5/10</span><span>5/12</span><span>5/14</span><span>5/16</span><span>5/18</span><span>5/20</span></div></article>
      </div>
      <div class="report-bottom-grid">
        <article class="insight-card strengths"><h2>♙ 优势亮点</h2><ul><li>专业知识扎实，技术基础牢固</li><li>项目经验丰富，解决问题思路清晰</li><li>沟通表达流畅，逻辑性强</li></ul></article>
        <article class="insight-card weaknesses"><h2>※ 待提升项</h2><ul><li v-for="item in report.weaknesses" :key="item">{{ item }}</li></ul></article>
        <article class="insight-card suggestions"><h2>⊙ AI 建议</h2><p v-for="item in report.suggestions" :key="item">{{ item }}</p></article>
      </div>
    </section>
  </LayoutShell>
</template>
