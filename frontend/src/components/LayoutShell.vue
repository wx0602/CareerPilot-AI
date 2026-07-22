<script setup>
import { useRouter } from 'vue-router';
import AppIcon from './AppIcon.vue';
import BrandLogo from './BrandLogo.vue';
import { api, clearAuth } from '../api/client';

const router = useRouter();

const nav = [
  { to: '/dashboard', label: '场景选择', icon: 'grid' },
  { to: { path: '/upload', query: { new: '1' } }, label: '上传简历', icon: 'practice' },
  { to: '/study-plan', label: '学习计划', icon: 'plan' },
  { to: '/job-recommendations', label: '岗位推荐', icon: 'briefcase' },
  { to: '/report', label: '我的报告', icon: 'report' },
  { to: '/favorites', label: '收藏题库', icon: 'star' },
  { to: '/avatar', label: '数字人展示', icon: 'practice' },
  { to: '/me', label: '我的', icon: 'user' }
];

async function logout() {
  try {
    await api.logout();
  } catch {
    // 本地登录状态仍需清理，避免失效令牌把用户困在应用中。
  } finally {
    clearAuth();
    router.push('/login');
  }
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <BrandLogo />
      <nav class="nav-list" aria-label="主导航">
        <RouterLink v-for="item in nav" :key="item.label" :to="item.to">
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <button class="logout-link" type="button" @click="logout">
        <AppIcon name="logout" />退出登录
      </button>
    </aside>
    <main class="main-area"><slot /></main>
  </div>
</template>
