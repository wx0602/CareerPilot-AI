<script setup>
import AppIcon from './AppIcon.vue';
import BrandLogo from './BrandLogo.vue';

const nav = [
  { to: '/dashboard', label: '场景选择', icon: 'grid' },
  { to: { path: '/upload', query: { new: '1' } }, label: '上传简历', icon: 'practice' },
  { to: '/study-plan', label: '学习计划', icon: 'plan' },
  { to: '/report', label: '我的报告', icon: 'report' },
  { to: '/favorites', label: '收藏题库', icon: 'star' },
  { to: '/avatar', label: '数字人展示', icon: 'practice' },
  { to: '/settings', label: '设置', icon: 'settings' }
];
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
      <RouterLink class="logout-link" to="/login">
        <AppIcon name="logout" />退出登录
      </RouterLink>
    </aside>
    <main class="main-area"><slot /></main>
  </div>
</template>
