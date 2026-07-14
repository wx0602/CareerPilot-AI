<script setup>
import { ref } from 'vue';
import LayoutShell from '../components/LayoutShell.vue';

const apiBase = ref(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000');
const enableRealApi = ref(true);
const saveMessage = ref('');

function save() {
  saveMessage.value = '设置已保存到当前页面状态。环境变量仍需在启动前配置。';
}
</script>

<template>
  <LayoutShell>
    <section class="page upload-page">
      <header><h1>设置</h1><p>管理本地联调参数和练习偏好。</p></header>
      <div class="uploaded-file">
        <span>API</span>
        <div>
          <strong>后端地址</strong>
          <input v-model="apiBase" type="text" />
        </div>
      </div>
      <div class="uploaded-file">
        <span>模式</span>
        <div>
          <strong>真实接口调用</strong>
          <small>当前前端通过 VITE_API_BASE_URL 调用后端。</small>
        </div>
        <input v-model="enableRealApi" type="checkbox" />
      </div>
      <p class="privacy-note">{{ saveMessage || '设置页已与数字人展示、收藏题库分离。' }}</p>
      <div class="page-actions"><button class="primary-button next-button" @click="save">保存设置</button></div>
    </section>
  </LayoutShell>
</template>
