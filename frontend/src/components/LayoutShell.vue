<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">CP</span>
        <span>
          <strong>CareerPilot AI</strong>
          <small>智能实训平台</small>
        </span>
      </RouterLink>

      <nav class="nav-list" aria-label="主导航">
        <RouterLink to="/">场景</RouterLink>
        <RouterLink to="/login">登录</RouterLink>
        <RouterLink to="/upload">上传</RouterLink>
        <RouterLink to="/exam">笔试</RouterLink>
        <RouterLink to="/interview">面试</RouterLink>
        <RouterLink to="/report">报告</RouterLink>
        <RouterLink to="/avatar">数字人</RouterLink>
      </nav>
    </aside>

    <main class="main-area">
      <RouterView />
    </main>
  </div>
</template>
