<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import BrandLogo from '../components/BrandLogo.vue';
import AppIcon from '../components/AppIcon.vue';
import { api, clearSession, setToken } from '../api/client';

const router = useRouter();
const account = ref('');
const password = ref('');
const authMode = ref('login');
const loading = ref(false);
const message = ref('');

async function enter(asGuest = false) {
  if (!asGuest && (!account.value || !password.value)) {
    message.value = '请填写账号和密码';
    return;
  }
  loading.value = true;
  message.value = '';
  try {
    const auth = asGuest
      ? await api.guest()
      : authMode.value === 'register'
        ? await api.register({ account: account.value, password: password.value })
        : await api.login({ account: account.value, password: password.value, remember_me: true });
    setToken(auth.access_token);
    clearSession();
    router.push('/dashboard');
  } catch (error) {
    message.value = error.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-pitch">
      <BrandLogo />
      <div class="pitch-copy">
        <p class="eyebrow">CAREER · PRACTICE · GROWTH</p>
        <h1>你的 <em>AI</em> 面试备考助手</h1>
        <p>智能练习 · 精准反馈 · 高效提升</p>
        <ul class="feature-list">
          <li><b>⌘</b><span><strong>全真场景模拟</strong><small>覆盖笔试、面试、路演答辩等真实场景</small></span></li>
          <li><b>♙</b><span><strong>AI 智能评估</strong><small>多维度分析反馈，给出个性化建议</small></span></li>
          <li><b>▤</b><span><strong>数据驱动提升</strong><small>追踪学习轨迹，持续优化备考策略</small></span></li>
        </ul>
      </div>
      <div class="pitch-visual" aria-hidden="true"><i></i><i></i><i></i><div class="visual-ring">↗</div></div>
    </section>

    <section class="login-stage">
      <div class="welcome-panel">
        <BrandLogo />
        <div><h2>欢迎回来</h2><p>登录以继续你的备考之旅</p></div>
        <ul>
          <li><b>▧</b><span><strong>个性化学习计划</strong><small>根据目标岗位定制学习路径</small></span></li>
          <li><b>◇</b><span><strong>多维度能力评估</strong><small>科学分析，精准定位薄弱点</small></span></li>
          <li><b>☆</b><span><strong>全程智能同步</strong><small>学习进度云端保存，随时继续</small></span></li>
        </ul>
      </div>
      <form class="login-card" @submit.prevent="enter(false)">
        <h2>{{ authMode === 'login' ? '账号登录' : '注册账号' }}</h2>
        <label>邮箱 / 手机号<input v-model="account" type="text" placeholder="demo@careerpilot.local" /></label>
        <label>密码<input v-model="password" type="password" placeholder="Demo123!" /></label>
        <div class="form-meta"><label class="check-label"><input type="checkbox" />记住我</label><a href="#">忘记密码？</a></div>
        <p v-if="message" class="form-error">{{ message }}</p>
        <button class="primary-button" type="submit" :disabled="loading">{{ loading ? '处理中...' : (authMode === 'login' ? '登录' : '注册并登录') }}</button>
        <div class="or"><span>或</span></div>
        <button class="ghost-button" type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'">
          {{ authMode === 'login' ? '没有账号？立即注册' : '已有账号？返回登录' }}
        </button>
        <button class="guest-button" type="button" :disabled="loading" @click="enter(true)">
          <AppIcon name="practice" />游客模式进入<small>无需注册，快速体验</small>
        </button>
        <p class="terms">登录即代表同意《用户协议》和《隐私政策》</p>
      </form>
    </section>
  </main>
</template>
