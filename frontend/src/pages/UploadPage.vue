<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';

const router = useRouter();
const active = ref('简历');
const file = ref(null);
const types = ['简历', '职位描述（JD）', '项目资料', '其他材料'];
function choose(event) { file.value = event.target.files?.[0] || null; }
</script>

<template>
  <LayoutShell>
    <section class="page upload-page">
      <header><h1>上传你的材料</h1><p>上传简历和相关材料，让 AI 更好地了解你，提供更精准的练习体验</p></header>
      <div class="material-tabs"><button v-for="type in types" :key="type" :class="{ active: active === type }" @click="active = type">{{ type }}</button></div>
      <label class="dropzone">
        <input type="file" accept=".pdf,.doc,.docx,.txt" @change="choose" />
        <span class="cloud-icon"><AppIcon name="upload" /></span>
        <strong>点击或拖拽文件到此处上传</strong>
        <small>支持 PDF、DOC、DOCX 格式，文件大小不超过 10MB</small>
      </label>
      <div v-if="file" class="uploaded-file"><span>▣</span><div><strong>{{ file.name }}</strong><small>{{ (file.size / 1024 / 1024).toFixed(2) }} MB</small><i><b></b></i></div><em>100%</em><span class="success">✓</span></div>
      <p class="privacy-note">♙ 我们只会将材料用于你的练习，效果更佳</p>
      <div class="page-actions"><button class="primary-button next-button" :disabled="!file" @click="router.push('/dashboard')">下一步 <AppIcon name="arrow" /></button></div>
    </section>
  </LayoutShell>
</template>
