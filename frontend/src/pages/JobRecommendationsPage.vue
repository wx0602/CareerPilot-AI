<script setup>
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import LayoutShell from '../components/LayoutShell.vue';
import { api, getSession, setSession } from '../api/client';

const router = useRouter();
const source = ref('resume');
const resumeFile = ref(null);
const resumeSessionId = ref(null);
const uploadState = ref('');
const building = ref(false);
const searching = ref(false);
const interviewingJobId = ref('');
const error = ref('');
const emptyMessage = ref('');
const jobs = ref([]);
const profileReady = ref(false);

const profile = reactive({
  target_position: '',
  expected_city: '',
  expected_salary_min: null,
  expected_salary_max: null,
  expected_salary_currency: 'CNY',
  expected_salary_period: 'MONTH',
  education: '',
  years_of_experience: null,
  core_skills: [],
  project_experience: [],
  weak_skills: [],
  recent_report_score: null,
  source: 'resume'
});

const sourceOptions = [
  { value: 'resume', title: '使用简历', text: '从 PDF / DOCX 简历生成求职画像' },
  { value: 'recent_report', title: '使用最近报告', text: '读取最近一次笔试或面试报告' },
  { value: 'combined', title: '简历 + 报告', text: '综合经历、技能与最近评估表现' }
];

const needsResume = computed(() => ['resume', 'combined'].includes(source.value));
const hasProfile = computed(() => profileReady.value && profile.target_position.trim());

function assignProfile(data) {
  Object.assign(profile, {
    ...data,
    core_skills: data.core_skills || [],
    project_experience: data.project_experience || [],
    weak_skills: data.weak_skills || []
  });
}

function splitList(value, separator = /[,，;；\n]/) {
  return [...new Set(value.split(separator).map((item) => item.trim()).filter(Boolean))];
}

function updateList(field, event) {
  profile[field] = splitList(event.target.value);
}

async function chooseResume(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  resumeFile.value = file;
  error.value = '';
  uploadState.value = '正在上传并解析简历...';
  try {
    let session = getSession();
    if (!session) {
      session = await api.createSession({ mode: 'job', position: '岗位推荐画像' });
      setSession(session);
    }
    resumeSessionId.value = session.session_id;
    const uploaded = await api.uploadMaterial({
      sessionId: session.session_id,
      materialType: 'resume',
      file
    });
    if (uploaded.parse_status !== 'parsed') {
      throw new Error(uploaded.parse_error || '简历解析失败');
    }
    uploadState.value = `已解析：${uploaded.filename}`;
  } catch (err) {
    uploadState.value = '';
    error.value = err.message;
  }
}

async function buildProfile() {
  error.value = '';
  emptyMessage.value = '';
  jobs.value = [];
  building.value = true;
  try {
    const data = await api.buildJobProfile({
      source: source.value,
      session_id: resumeSessionId.value
    });
    assignProfile(data);
    profileReady.value = true;
  } catch (err) {
    error.value = err.message;
  } finally {
    building.value = false;
  }
}

async function searchJobs() {
  if (!profile.target_position.trim()) {
    error.value = '请先填写目标岗位';
    return;
  }
  error.value = '';
  emptyMessage.value = '';
  searching.value = true;
  try {
    profile.source = source.value;
    const data = await api.searchJobRecommendations(profile);
    jobs.value = data.jobs || [];
    emptyMessage.value = jobs.value.length ? '' : (data.message || '');
  } catch (err) {
    error.value = err.message;
  } finally {
    searching.value = false;
  }
}

async function startInterview(job) {
  interviewingJobId.value = job.job_id;
  error.value = '';
  try {
    const session = await api.startJobInterview(profile, job);
    setSession(session);
    await router.push('/interview');
  } catch (err) {
    error.value = err.message;
    interviewingJobId.value = '';
  }
}

function formatPostedAt(value) {
  if (!value) return '发布时间未公开';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('zh-CN');
}

function matchModeLabel(mode) {
  return {
    strict: '严格匹配',
    relaxed_salary_experience: '已放宽薪资与经验',
    relaxed_city: '已放宽城市',
    expanded_synonyms: '已扩展岗位同义词',
    seed_fallback: '种子库兜底'
  }[mode] || '综合匹配';
}
</script>

<template>
  <LayoutShell>
    <section class="page job-recommendation-page">
      <header class="job-page-header">
        <div>
          <p class="eyebrow">REAL JOBS · PROFILE MATCHING</p>
          <h1>岗位推荐</h1>
          <p>结合简历与评估报告生成求职画像，优先搜索实时岗位并以企业官方种子库兜底。</p>
        </div>
        <span>Top 10 智能匹配</span>
      </header>

      <p v-if="error" class="profile-alert error">{{ error }}</p>

      <section class="job-workflow-card">
        <div class="job-step-title"><b>1</b><div><h2>选择画像来源</h2><p>你可以单独使用简历或报告，也可以综合生成。</p></div></div>
        <div class="profile-source-grid">
          <button
            v-for="item in sourceOptions"
            :key="item.value"
            type="button"
            :class="{ active: source === item.value }"
            @click="source = item.value"
          >
            <strong>{{ item.title }}</strong><small>{{ item.text }}</small>
          </button>
        </div>

        <label v-if="needsResume" class="resume-upload-box">
          <AppIcon name="upload" />
          <span><strong>{{ resumeFile?.name || '上传 PDF / DOCX 简历' }}</strong><small>{{ uploadState || '也可以直接使用账号最近一次成功解析的简历' }}</small></span>
          <input type="file" accept=".pdf,.docx" @change="chooseResume" />
        </label>

        <div class="job-step-actions">
          <button class="primary-button" type="button" :disabled="building" @click="buildProfile">
            {{ building ? '正在生成画像...' : '生成求职画像' }}
          </button>
        </div>
      </section>

      <section v-if="profileReady" class="job-workflow-card profile-editor-card">
        <div class="job-step-title"><b>2</b><div><h2>确认并编辑求职画像</h2><p>搜索前请确认信息准确，任何字段都可以修改。</p></div></div>
        <div class="job-profile-form">
          <label><span>目标岗位</span><input v-model="profile.target_position" placeholder="例如：Java 后端工程师" /></label>
          <label><span>期望城市</span><input v-model="profile.expected_city" placeholder="例如：上海" /></label>
          <div class="salary-fields">
            <span>期望薪资</span>
            <input v-model.number="profile.expected_salary_min" type="number" min="0" placeholder="最低" />
            <i>—</i>
            <input v-model.number="profile.expected_salary_max" type="number" min="0" placeholder="最高" />
            <select v-model="profile.expected_salary_currency"><option>CNY</option><option>USD</option><option>EUR</option></select>
            <select v-model="profile.expected_salary_period"><option value="MONTH">月</option><option value="YEAR">年</option></select>
          </div>
          <label><span>学历</span><input v-model="profile.education" placeholder="例如：本科 · 计算机科学" /></label>
          <label><span>工作经验（年）</span><input v-model.number="profile.years_of_experience" type="number" min="0" step="0.5" /></label>
          <label class="wide"><span>核心技能</span><textarea :value="profile.core_skills.join('，')" placeholder="Java，Spring Boot，MySQL" @input="updateList('core_skills', $event)"></textarea></label>
          <label class="wide"><span>项目经历（每行一项）</span><textarea :value="profile.project_experience.join('\n')" @input="updateList('project_experience', $event)"></textarea></label>
          <label class="wide"><span>薄弱技能</span><textarea :value="profile.weak_skills.join('，')" @input="updateList('weak_skills', $event)"></textarea></label>
        </div>
        <div v-if="profile.recent_report_score !== null" class="report-score-note">最近评估报告：<b>{{ profile.recent_report_score }}</b> 分</div>
        <div class="job-step-actions">
          <button class="primary-button" type="button" :disabled="searching || !hasProfile" @click="searchJobs">
            {{ searching ? '正在搜索真实岗位...' : '确认画像并搜索岗位' }}
          </button>
        </div>
      </section>

      <section v-if="jobs.length || emptyMessage" class="job-results-section">
        <div class="job-results-head"><div><h2>为你推荐的岗位</h2><p>岗位事实与薪资来自实时岗位源或企业官方招聘页面，未公开薪资不会估算。</p></div><span>{{ jobs.length }} 个结果</span></div>
        <div v-if="emptyMessage" class="job-empty">{{ emptyMessage }}</div>
        <article v-for="job in jobs" :key="job.job_id" class="job-result-card">
          <div class="job-match-score"><b>{{ job.match_score }}</b><span>% 匹配</span></div>
          <div class="job-result-main">
            <div class="job-result-title">
              <div><h3>{{ job.title }}</h3><p>{{ job.company_name }} · {{ job.city }}</p></div>
              <strong>{{ job.salary_display }}</strong>
            </div>
            <div class="job-meta"><span>{{ job.employment_type || '工作类型未公开' }}</span><span>{{ formatPostedAt(job.posted_at) }}</span><span>来源：{{ job.data_source }}</span><span>{{ matchModeLabel(job.match_mode) }}</span><span v-if="job.link_status === 'inactive'">原链接可能已失效</span></div>
            <p class="job-description">{{ job.description || '岗位描述未公开' }}</p>
            <div class="job-reason"><b>推荐理由</b><p>{{ job.recommendation_reason }}</p></div>
            <div class="skill-comparison">
              <div><b>已匹配技能</b><span v-for="skill in job.matched_skills" :key="skill" class="skill matched">{{ skill }}</span><small v-if="!job.matched_skills.length">暂无明确匹配项</small></div>
              <div><b>缺失技能</b><span v-for="skill in job.missing_skills" :key="skill" class="skill missing">{{ skill }}</span><small v-if="!job.missing_skills.length">未发现明显缺口</small></div>
            </div>
            <div v-if="job.improvement_suggestions.length" class="job-advice"><b>改进建议</b><ul><li v-for="item in job.improvement_suggestions" :key="item">{{ item }}</li></ul></div>
            <div class="job-card-actions">
              <a :href="job.link_status === 'inactive' ? undefined : job.apply_link" target="_blank" rel="noopener noreferrer" :class="['outline-button', { disabled: !job.apply_link || job.link_status === 'inactive' }]">{{ job.link_status === 'inactive' ? '原岗位可能已失效' : '查看原岗位' }}</a>
              <button class="primary-button" type="button" :disabled="interviewingJobId === job.job_id" @click="startInterview(job)">
                {{ interviewingJobId === job.job_id ? '正在准备...' : '针对该岗位模拟面试' }}
              </button>
            </div>
          </div>
        </article>
      </section>
    </section>
  </LayoutShell>
</template>
