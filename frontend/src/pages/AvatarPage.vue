<script setup>
import { ref } from 'vue';
import LayoutShell from '../components/LayoutShell.vue';
const selected = ref(0);
const started = ref(false);
const avatars = ['林', '安', '岚'];
</script>

<template>
  <LayoutShell>
    <section class="avatar-page">
      <div class="avatar-stage-full">
        <div class="halo"></div>
        <div class="digital-human">
          <div class="hair"></div><div class="face"><i></i><i></i><b></b></div><div class="neck"></div><div class="body"><span></span><span></span></div>
        </div>
        <div class="avatar-controls"><button>▶</button><button>↻</button><button>▶|</button><button>◉</button><button>⛶</button></div>
      </div>
      <aside class="avatar-settings">
        <h1>数字人设置</h1><label>形象</label><div class="avatar-picks"><button v-for="(avatar, i) in avatars" :key="avatar" :class="{ active: selected === i }" @click="selected = i"><span>{{ avatar }}</span></button></div>
        <label>音色</label><select><option>小悦（温和亲切）</option><option>小川（沉稳专业）</option></select>
        <label>语速</label><div class="range-row"><small>慢</small><input type="range" min="1" max="5" value="3" /><small>快</small></div>
        <label>背景</label><div class="background-picks"><button class="active"></button><button></button><button></button><button></button></div>
        <button class="primary-button start-avatar" @click="started = !started">{{ started ? '暂停训练' : '开始训练' }}</button>
      </aside>
    </section>
  </LayoutShell>
</template>
