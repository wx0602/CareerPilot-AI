<script setup>
import { onMounted, ref } from 'vue';
import LayoutShell from '../components/LayoutShell.vue';
import { api } from '../api/client';

const favorites = ref([]);
const loading = ref(false);
const error = ref('');

onMounted(loadFavorites);

async function loadFavorites() {
  loading.value = true;
  error.value = '';
  try {
    favorites.value = await api.listFavorites();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function remove(questionId) {
  try {
    await api.removeFavorite(questionId);
    favorites.value = favorites.value.filter((item) => item.question_id !== questionId);
  } catch (err) {
    error.value = err.message;
  }
}
</script>

<template>
  <LayoutShell>
    <section class="page dashboard-page">
      <header class="dashboard-header">
        <div><h1>收藏题库</h1><p>这里展示你在笔试中收藏的真实题目。</p></div>
        <div class="practice-summary">已收藏 <b>{{ favorites.length }}</b> 题</div>
      </header>
      <p v-if="loading" class="privacy-note">加载中...</p>
      <p v-if="error" class="form-error">{{ error }}</p>
      <div class="scenario-grid">
        <article v-for="item in favorites" :key="item.favorite_id" class="scenario-card">
          <span class="scenario-icon blue">★</span>
          <h2>{{ item.content }}</h2>
          <p>{{ item.question_type }}</p>
          <small>{{ item.question_id }}</small>
          <button class="outline-button" @click="remove(item.question_id)">取消收藏</button>
        </article>
      </div>
      <p v-if="!loading && favorites.length === 0" class="privacy-note">还没有收藏题目。进入笔试后点击“收藏”即可加入这里。</p>
    </section>
  </LayoutShell>
</template>
