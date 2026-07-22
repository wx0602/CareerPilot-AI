<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, clearAuth, getAuthUser, setAuthUser } from '../api/client';
import { learningModules } from '../data/learningModules';

const router = useRouter();
const loading = ref(true);
const saving = ref(false);
const error = ref('');
const success = ref('');
const profile = ref({
  user: getAuthUser() || { is_guest: true, avatar_preset: 'blue' },
  stats: {
    completed_practices: 0,
    answered_questions: 0,
    favorite_questions: 0,
    report_count: 0,
    last_study_at: null
  }
});

const form = reactive({
  nickname: '',
  avatar_preset: 'blue',
  target_position: '',
  career_stage: ''
});

const avatarPresets = [
  { id: 'blue', label: '海盐蓝' },
  { id: 'violet', label: '星云紫' },
  { id: 'green', label: '青竹绿' },
  { id: 'orange', label: '暖阳橙' }
];

const careerStages = [
  { value: 'student', label: '在校生' },
  { value: 'new_grad', label: '应届生' },
  { value: 'experienced', label: '社招求职' },
  { value: 'career_switch', label: '转行求职' }
];

const positionOptions = [...new Set(learningModules.map((item) => item.position))];
const isGuest = computed(() => Boolean(profile.value.user?.is_guest));
const displayName = computed(() => {
  if (profile.value.user?.nickname) return profile.value.user.nickname;
  if (isGuest.value) return '游客用户';
  return profile.value.user?.account?.split('@')[0] || 'CareerPilot 用户';
});
const avatarLetter = computed(() => displayName.value.trim().slice(0, 1).toUpperCase() || 'C');
const targetLabel = computed(() => profile.value.user?.target_position || '还未设置目标岗位');
const stageLabel = computed(
  () => careerStages.find((item) => item.value === profile.value.user?.career_stage)?.label || '求职阶段未设置'
);

function fillForm(user) {
  form.nickname = user?.nickname || '';
  form.avatar_preset = user?.avatar_preset || 'blue';
  form.target_position = user?.target_position || '';
  form.career_stage = user?.career_stage || '';
}

function maskAccount(account) {
  if (!account) return '游客账号';
  if (account.includes('@')) {
    const [name, domain] = account.split('@');
    return `${name.slice(0, 2)}***@${domain}`;
  }
  if (account.length > 7) return `${account.slice(0, 3)}****${account.slice(-4)}`;
  return account;
}

function formatDate(value) {
  if (!value) return '暂无记录';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date(value));
}

function scrollToProfileForm() {
  document.getElementById('profile-form')?.scrollIntoView({ behavior: 'smooth' });
}

async function loadProfile() {
  loading.value = true;
  error.value = '';
  try {
    profile.value = await api.getMyProfile();
    fillForm(profile.value.user);
    setAuthUser(profile.value.user);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function saveProfile() {
  error.value = '';
  success.value = '';
  if (form.nickname.trim().length < 2) {
    error.value = '昵称至少需要 2 个字符';
    return;
  }
  saving.value = true;
  try {
    profile.value = await api.updateMyProfile({
      nickname: form.nickname.trim(),
      avatar_preset: form.avatar_preset,
      target_position: form.target_position || null,
      career_stage: form.career_stage || null
    });
    setAuthUser(profile.value.user);
    fillForm(profile.value.user);
    success.value = '个人资料已保存';
  } catch (err) {
    error.value = err.message;
  } finally {
    saving.value = false;
  }
}

async function leaveAccount() {
  try {
    await api.logout();
  } catch {
    // 令牌即使已经失效，也允许用户清理本地状态。
  } finally {
    clearAuth();
    router.push('/login');
  }
}

onMounted(loadProfile);
</script>

<template>
  <LayoutShell>
    <section class="page profile-page">
      <header class="profile-heading">
        <div>
          <h1>我的</h1>
          <p>管理个人资料，查看你的练习成长记录。</p>
        </div>
        <span v-if="isGuest" class="profile-status guest">游客模式</span>
        <span v-else class="profile-status">资料已同步</span>
      </header>

      <p v-if="error" class="profile-alert error">{{ error }}</p>
      <p v-if="success" class="profile-alert success">{{ success }}</p>

      <div v-if="loading" class="profile-loading">正在加载个人资料...</div>

      <template v-else>
        <section class="profile-hero">
          <div class="profile-avatar" :class="profile.user.avatar_preset || 'blue'">
            {{ avatarLetter }}
          </div>
          <div class="profile-identity">
            <div class="profile-name-row">
              <h2>{{ displayName }}</h2>
              <span>{{ isGuest ? '游客' : '正式账号' }}</span>
            </div>
            <p>{{ targetLabel }} · {{ stageLabel }}</p>
            <small>{{ maskAccount(profile.user.account) }}</small>
          </div>
          <button v-if="!isGuest" class="outline-button" type="button" @click="scrollToProfileForm">
            编辑资料
          </button>
        </section>

        <section class="profile-stats" aria-label="学习数据">
          <article>
            <b>{{ profile.stats.completed_practices }}</b>
            <span>完成练习</span>
          </article>
          <article>
            <b>{{ profile.stats.answered_questions }}</b>
            <span>累计答题</span>
          </article>
          <article>
            <b>{{ profile.stats.favorite_questions }}</b>
            <span>收藏题目</span>
          </article>
          <article>
            <b>{{ profile.stats.report_count }}</b>
            <span>能力报告</span>
          </article>
        </section>

        <section v-if="isGuest" class="guest-profile-card">
          <div>
            <strong>注册账号，保存你的成长记录</strong>
            <p>游客资料和练习记录无法跨设备同步，登录或注册后即可长期保存。</p>
          </div>
          <button class="primary-button" type="button" @click="leaveAccount">登录 / 注册</button>
        </section>

        <div class="profile-grid">
          <section id="profile-form" class="profile-card profile-form-card">
            <div class="profile-card-head">
              <div>
                <h2>个人资料</h2>
                <p>{{ isGuest ? '注册后即可编辑并同步资料' : '这些信息会用于个性化学习体验' }}</p>
              </div>
            </div>

            <fieldset :disabled="isGuest || saving">
              <label class="profile-field">
                <span>昵称</span>
                <input v-model="form.nickname" maxlength="20" placeholder="请输入 2～20 个字符" />
              </label>

              <div class="profile-field">
                <span>头像风格</span>
                <div class="avatar-options">
                  <button
                    v-for="item in avatarPresets"
                    :key="item.id"
                    type="button"
                    :class="['avatar-option', item.id, { active: form.avatar_preset === item.id }]"
                    :aria-label="item.label"
                    @click="form.avatar_preset = item.id"
                  >
                    {{ form.nickname.trim().slice(0, 1) || avatarLetter }}
                  </button>
                </div>
              </div>

              <label class="profile-field">
                <span>目标岗位</span>
                <select v-model="form.target_position">
                  <option value="">暂未确定</option>
                  <option v-for="position in positionOptions" :key="position" :value="position">
                    {{ position }}
                  </option>
                </select>
              </label>

              <label class="profile-field">
                <span>求职阶段</span>
                <select v-model="form.career_stage">
                  <option value="">请选择</option>
                  <option v-for="item in careerStages" :key="item.value" :value="item.value">
                    {{ item.label }}
                  </option>
                </select>
              </label>
            </fieldset>

            <div v-if="!isGuest" class="profile-form-actions">
              <button class="primary-button" type="button" :disabled="saving" @click="saveProfile">
                {{ saving ? '保存中...' : '保存资料' }}
              </button>
            </div>
          </section>

          <aside class="profile-side">
            <section class="profile-card">
              <div class="profile-card-head">
                <div><h2>学习中心</h2><p>快速回到你的学习内容</p></div>
              </div>
              <button class="profile-link" type="button" @click="router.push('/report')">
                <span><AppIcon name="report" />我的报告</span><b>›</b>
              </button>
              <button class="profile-link" type="button" @click="router.push('/favorites')">
                <span><AppIcon name="star" />收藏题库</span><b>›</b>
              </button>
              <button class="profile-link" type="button" @click="router.push('/study-plan')">
                <span><AppIcon name="plan" />学习计划</span><b>›</b>
              </button>
            </section>

            <section class="profile-card account-card">
              <div class="profile-card-head">
                <div><h2>账号信息</h2><p>登录状态与数据同步</p></div>
              </div>
              <dl>
                <div><dt>当前账号</dt><dd>{{ maskAccount(profile.user.account) }}</dd></div>
                <div><dt>最近学习</dt><dd>{{ formatDate(profile.stats.last_study_at) }}</dd></div>
              </dl>
              <button class="profile-logout" type="button" @click="leaveAccount">退出登录</button>
            </section>
          </aside>
        </div>
      </template>
    </section>
  </LayoutShell>
</template>
