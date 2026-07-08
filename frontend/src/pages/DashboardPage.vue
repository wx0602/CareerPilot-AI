<template>
  <section class="page">
    <header class="page-header">
      <p>场景选择</p>
      <h1>训练工作台</h1>
    </header>

    <div class="scenario-grid">
      <RouterLink class="scenario-tile" to="/exam">企业笔试</RouterLink>
      <RouterLink class="scenario-tile" to="/interview">数字人面试</RouterLink>
      <RouterLink class="scenario-tile" to="/interview">技术面试</RouterLink>
      <RouterLink class="scenario-tile" to="/avatar">创业路演</RouterLink>
      <RouterLink class="scenario-tile" to="/report">综合训练</RouterLink>
    </div>
  </section>
</template>
