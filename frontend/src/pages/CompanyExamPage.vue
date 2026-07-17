<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import LayoutShell from '../components/LayoutShell.vue';
import { api, getSession, setSession } from '../api/client';
import { companyExams, getCompany, getCompanyPosition } from '../data/companyExams';

const router = useRouter();
const session = ref(getSession());
const initialCompany = getCompany(session.value?.company) || companyExams[0] || null;
const initialPosition = getCompanyPosition(initialCompany?.id, session.value?.position);
const selectedCompanyId = ref(initialCompany?.id || '');
const selectedPositionId = ref(initialPosition?.id || '');
const loading = ref(false);
const error = ref('');

const companyVisuals = {
  alibaba: { mark: '阿', accent: '#ff6a00', soft: '#fff3e9' },
  jd: { mark: '京', accent: '#e1251b', soft: '#fff0ef' },
  meituan: { mark: '美', accent: '#d99b00', soft: '#fff8df' },
  xiaohongshu: { mark: 'RED', accent: '#ff2442', soft: '#fff0f3' },
  xiaomi: { mark: 'MI', accent: '#ff6900', soft: '#fff3e8' }
};

const selectedCompany = computed(() => getCompany(selectedCompanyId.value));
const selectedPosition = computed(() =>
  getCompanyPosition(selectedCompanyId.value, selectedPositionId.value)
);
const questionCount = computed(() =>
  Object.values(selectedPosition.value?.questionMix || {}).reduce(
    (total, value) => total + Number(value || 0),
    0
  )
);
const totalPositionCount = computed(() =>
  companyExams.reduce((total, company) => total + company.positions.length, 0)
);

function companyVisual(company) {
  return companyVisuals[company?.id] || { mark: company?.name?.slice(0, 1) || '企', accent: '#2877f2', soft: '#eef5ff' };
}

function companyTheme(company) {
  const visual = companyVisual(company);
  return { '--brand': visual.accent, '--brand-soft': visual.soft };
}

function selectCompany(company) {
  selectedCompanyId.value = company.id;
  if (!company.positions.some((item) => item.id === selectedPositionId.value)) {
    selectedPositionId.value = '';
  }
  error.value = '';
}

function selectPosition(position) {
  selectedPositionId.value = position.id;
  error.value = '';
}

async function startExam() {
  if (!session.value) {
    await router.push('/dashboard');
    return;
  }
  if (!selectedCompany.value || !selectedPosition.value) {
    error.value = '请先选择企业和应聘岗位。';
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    const updated = await api.updateSession(session.value.session_id, {
      company: selectedCompany.value.id,
      position: selectedPosition.value.id,
      learning_module: 'company_exam',
      learning_module_title: selectedPosition.value.title,
      question_mix: selectedPosition.value.questionMix
    });
    setSession(updated);
    session.value = updated;
    await router.push('/exam');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <LayoutShell>
    <section class="page company-exam-page">
      <header class="company-header">
        <div class="header-copy">
          <button class="back-link" @click="router.push('/scene/written')">
            <AppIcon name="back" />返回企业笔试介绍
          </button>
          <span class="company-eyebrow">COMPANY ASSESSMENT</span>
          <h1>找到你的目标，<em>开始实战</em></h1>
          <p>选择目标企业与应聘岗位，使用独立真实题库完成一次完整笔试。</p>
        </div>
        <div class="header-overview">
          <div><strong>{{ companyExams.length }}</strong><span>家企业</span></div>
          <i></i>
          <div><strong>{{ totalPositionCount }}</strong><span>个岗位</span></div>
          <i></i>
          <div><strong>专项</strong><span>能力报告</span></div>
        </div>
      </header>

      <section class="selector-section company-section">
        <div class="section-heading">
          <div><span>01</span><div><h2>选择目标企业</h2><p>不同企业使用独立岗位题库</p></div></div>
          <small>已接入 {{ companyExams.length }} 家企业</small>
        </div>
        <div class="company-grid">
          <button
            v-for="company in companyExams"
            :key="company.id"
            class="company-card"
            :class="{ active: selectedCompanyId === company.id }"
            :style="companyTheme(company)"
            @click="selectCompany(company)"
          >
            <div class="company-card-top">
              <span class="company-mark">{{ companyVisual(company).mark }}</span>
              <span class="select-indicator">✓</span>
            </div>
            <div class="company-card-copy">
              <strong>{{ company.name }}</strong>
              <p>{{ company.description }}</p>
            </div>
            <div class="company-card-footer">
              <span>{{ company.positions.length }} 个岗位</span>
              <b>选择 <span>→</span></b>
            </div>
          </button>
        </div>
      </section>

      <section
        v-if="selectedCompany"
        class="selector-section position-section"
        :style="companyTheme(selectedCompany)"
      >
        <div class="section-heading">
          <div><span>02</span><div><h2>选择{{ selectedCompany.name }}的应聘岗位</h2><p>选择一个方向查看完整题型配比</p></div></div>
          <span class="selected-company"><b>{{ companyVisual(selectedCompany).mark }}</b>{{ selectedCompany.name }}</span>
        </div>
        <div class="position-grid">
          <button
            v-for="(position, index) in selectedCompany.positions"
            :key="position.id"
            class="position-card"
            :class="{ active: selectedPositionId === position.id }"
            @click="selectPosition(position)"
          >
            <div class="position-card-head">
              <span class="position-index">0{{ index + 1 }}</span>
              <span class="question-total">{{ Object.values(position.questionMix).reduce((sum, value) => sum + value, 0) }} 题</span>
            </div>
            <strong>{{ position.title }}</strong>
            <p>{{ position.summary }}</p>
            <dl>
              <div v-if="position.questionMix.single_choice"><dt>{{ position.questionMix.single_choice }}</dt><dd>单选</dd></div>
              <div v-if="position.questionMix.multiple_choice"><dt>{{ position.questionMix.multiple_choice }}</dt><dd>多选</dd></div>
              <div v-if="position.questionMix.true_false"><dt>{{ position.questionMix.true_false }}</dt><dd>判断</dd></div>
              <div v-if="position.questionMix.short_answer"><dt>{{ position.questionMix.short_answer }}</dt><dd>简答</dd></div>
            </dl>
          </button>
        </div>

        <p v-if="error" class="form-error">{{ error }}</p>

        <div class="exam-actions">
          <div class="selection-summary">
            <span class="selection-mark">{{ companyVisual(selectedCompany).mark }}</span>
            <div>
              <small>当前选择</small>
              <strong v-if="selectedPosition">{{ selectedCompany.name }} · {{ selectedPosition.title }}</strong>
              <strong v-else>{{ selectedCompany.name }} · 请选择应聘岗位</strong>
              <span v-if="selectedPosition">完整套题共 {{ questionCount }} 题，提交后自动生成报告</span>
              <span v-else>选择上方岗位后即可开始</span>
            </div>
          </div>
          <button class="primary-button" :disabled="loading || !selectedPosition" @click="startExam">
            {{ loading ? '正在创建试卷...' : '开始企业笔试' }}<b>→</b>
          </button>
        </div>
      </section>
    </section>
  </LayoutShell>
</template>

<style scoped>
.company-exam-page { max-width: 1280px; padding-top: 24px; padding-bottom: 60px; }
.company-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 36px; padding: 0 4px 28px; }
.company-header .back-link { margin: 0 0 22px -5px; font-size: 12px; }
.company-eyebrow { display: block; color: #2d6ed2; font-size: 9px; font-weight: 900; letter-spacing: 2.6px; }
.company-header h1 { margin: 9px 0 9px; color: #142844; font-family: Georgia, 'Songti SC', serif; font-size: clamp(32px, 3vw, 44px); line-height: 1.12; }
.company-header h1 em { color: #2877f2; font-style: normal; }
.company-header p { margin: 0; color: #7b8ba3; font-size: 13px; }
.header-overview { display: flex; align-items: center; flex: 0 0 auto; border: 1px solid #dae5f3; border-radius: 16px; padding: 14px 18px; background: rgba(255,255,255,.72); box-shadow: 0 10px 30px rgba(30,58,95,.06); }
.header-overview div { display: grid; min-width: 72px; text-align: center; }
.header-overview strong { color: #18355a; font-family: Georgia, serif; font-size: 20px; }
.header-overview span { margin-top: 2px; color: #8b9aae; font-size: 9px; }
.header-overview i { width: 1px; height: 28px; margin: 0 10px; background: #e1e8f1; }
.selector-section { margin-bottom: 20px; border: 1px solid #dce6f2; border-radius: 20px; padding: 22px; background: rgba(255,255,255,.94); box-shadow: 0 14px 40px rgba(31,58,94,.055); }
.section-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.section-heading > div { display: flex; align-items: center; gap: 11px; }
.section-heading > div > span { display: grid; width: 30px; height: 30px; flex: 0 0 auto; place-items: center; border-radius: 9px; color: #fff; background: #2877f2; font-size: 9px; font-weight: 900; box-shadow: 0 6px 14px rgba(40,119,242,.2); }
.position-section .section-heading > div > span { background: var(--brand); box-shadow: none; }
.section-heading h2 { margin: 0; color: #1a3558; font-size: 17px; }
.section-heading p { margin: 3px 0 0; color: #9aa7b8; font-size: 10px; }
.section-heading small { border-radius: 99px; padding: 6px 10px; color: #74859c; background: #f3f6fa; font-size: 9px; }
.company-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.company-card { position: relative; display: flex; min-height: 174px; flex-direction: column; overflow: hidden; border: 1px solid #e0e7f0; border-radius: 15px; padding: 16px; text-align: left; background: #fff; transition: .22s ease; }
.company-card:before { content: ''; position: absolute; top: 0; right: 0; width: 72px; height: 72px; border-radius: 0 0 0 72px; background: var(--brand-soft); opacity: .75; }
.company-card:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--brand) 35%, #dce5f0); box-shadow: 0 14px 26px rgba(30,53,86,.09); }
.company-card.active { border-color: var(--brand); background: linear-gradient(150deg,#fff 55%,var(--brand-soft)); box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 12%, transparent),0 14px 28px rgba(30,53,86,.09); }
.company-card-top { position: relative; display: flex; align-items: flex-start; justify-content: space-between; z-index: 1; }
.company-mark { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 11px; color: #fff; background: var(--brand); font-size: 13px; font-weight: 900; letter-spacing: -.5px; box-shadow: 0 7px 15px color-mix(in srgb, var(--brand) 24%, transparent); }
.select-indicator { display: grid; width: 20px; height: 20px; place-items: center; border: 1px solid #dce5ef; border-radius: 50%; color: transparent; background: rgba(255,255,255,.86); font-size: 10px; }
.company-card.active .select-indicator { border-color: var(--brand); color: #fff; background: var(--brand); }
.company-card-copy { flex: 1; }
.company-card-copy strong { display: block; margin-top: 13px; color: #173353; font-size: 15px; }
.company-card-copy p { min-height: 2.8em; margin: 5px 0 10px; color: #8795a8; font-size: 10px; line-height: 1.55; }
.company-card-footer { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid #edf1f6; padding-top: 10px; }
.company-card-footer > span { color: #8190a4; font-size: 9px; }
.company-card-footer b { color: var(--brand); font-size: 9px; }
.company-card-footer b span { display: inline-block; margin-left: 2px; transition: transform .2s; }
.company-card:hover .company-card-footer b span { transform: translateX(3px); }
.selected-company { display: flex; align-items: center; gap: 7px; color: #718198; font-size: 10px; }
.selected-company b { display: grid; min-width: 25px; height: 25px; place-items: center; border-radius: 8px; padding: 0 6px; color: #fff; background: var(--brand); font-size: 9px; }
.position-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 13px; }
.position-card { position: relative; border: 1px solid #dfe7f0; border-radius: 15px; padding: 17px; text-align: left; background: #fff; transition: .22s ease; }
.position-card:hover { transform: translateY(-2px); border-color: color-mix(in srgb, var(--brand) 42%, #dce5f0); box-shadow: 0 12px 24px rgba(30,53,86,.075); }
.position-card.active { border-color: var(--brand); background: linear-gradient(145deg,#fff 60%,var(--brand-soft)); box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand) 11%, transparent); }
.position-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.position-index { color: var(--brand); font-family: Georgia, serif; font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.question-total { border-radius: 99px; padding: 4px 8px; color: var(--brand); background: var(--brand-soft); font-size: 9px; font-weight: 800; }
.position-card > strong { color: #173353; font-size: 16px; }
.position-card > p { min-height: 2.8em; margin: 7px 0 0; color: #8492a5; font-size: 10px; line-height: 1.55; }
.position-card dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(52px, 1fr)); gap: 5px; margin: 15px 0 0; border-top: 1px solid #e8edf3; padding-top: 12px; }
.position-card dl div { border-radius: 8px; padding: 6px 4px; background: rgba(246,248,251,.85); text-align: center; }
.position-card dt { color: #273d59; font-size: 13px; font-weight: 900; }
.position-card dd { margin: 2px 0 0; color: #94a0b0; font-size: 8px; }
.form-error { margin: 12px 0 0; }
.exam-actions { display: flex; align-items: center; justify-content: space-between; gap: 24px; margin-top: 18px; border-radius: 14px; padding: 14px 16px; background: linear-gradient(100deg,var(--brand-soft),#f8fbff 55%,#f3f7fd); }
.selection-summary { display: flex; align-items: center; gap: 12px; min-width: 0; }
.selection-mark { display: grid; min-width: 40px; height: 40px; place-items: center; border-radius: 11px; padding: 0 7px; color: #fff; background: var(--brand); font-size: 11px; font-weight: 900; }
.selection-summary > div { display: grid; gap: 2px; }
.selection-summary small { color: #8b98aa; font-size: 8px; letter-spacing: 1px; }
.selection-summary strong { color: #173353; font-size: 13px; }
.selection-summary span:not(.selection-mark) { color: #8190a3; font-size: 9px; }
.exam-actions .primary-button { min-width: 174px; border-radius: 10px; padding: 11px 18px; background: var(--brand); box-shadow: 0 7px 16px color-mix(in srgb, var(--brand) 22%, transparent); font-size: 12px; }
.exam-actions .primary-button b { font-size: 14px; }
@media (max-width: 1100px) { .company-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 850px) {
  .company-header { align-items: flex-start; flex-direction: column; }
  .header-overview { display: none; }
  .company-grid { grid-template-columns: repeat(2, 1fr); }
  .position-grid { grid-template-columns: 1fr; }
  .exam-actions { align-items: stretch; flex-direction: column; }
  .exam-actions .primary-button { width: 100%; }
}
@media (max-width: 520px) {
  .company-grid { grid-template-columns: 1fr; }
  .section-heading > small,.selected-company { display: none; }
  .company-header h1 { font-size: 31px; }
}
</style>
