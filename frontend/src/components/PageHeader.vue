<script setup>
defineProps({ eyebrow: String, title: String, subtitle: String });
</script>
<template>
  <header class="page-header">
    <p v-if="eyebrow">{{ eyebrow }}</p><h1>{{ title }}</h1><span v-if="subtitle">{{ subtitle }}</span>
    <slot />
  </header>
</template>
