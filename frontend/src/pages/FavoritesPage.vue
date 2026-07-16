<script setup>
import { computed, onMounted, ref } from 'vue';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';
import { api } from '../api/client';

const favorites = ref([]);
const loading = ref(false);
const error = ref('');
const expandedId = ref(null);
const activeType = ref('all');
const keyword = ref('');

const typeLabels = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '简答题'
};

const typeFilters = [
  { value: 'all', label: '全部题目' },
  { value: 'single_choice', label: '单选题' },
  { value: 'multiple_choice', label: '多选题' },
  { value: 'true_false', label: '判断题' },
  { value: 'short_answer', label: '简答题' }
];

const typeCounts = computed(() => favorites.value.reduce((counts, item) => {
  counts[item.question_type] = (counts[item.question_type] || 0) + 1;
  return counts;
}, {}));

const filteredFavorites = computed(() => {
  const query = keyword.value.trim().toLowerCase();
  return favorites.value.filter((item) => {
    const matchesType = activeType.value === 'all' || item.question_type === activeType.value;
    const matchesKeyword = !query || item.content.toLowerCase().includes(query) || item.question_id.toLowerCase().includes(query);
    return matchesType && matchesKeyword;
  });
});

function filterCount(type) {
  return type === 'all' ? favorites.value.length : typeCounts.value[type] || 0;
}

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
    if (expandedId.value === questionId) expandedId.value = null;
  } catch (err) {
    error.value = err.message;
  }
}

function toggle(questionId) {
  expandedId.value = expandedId.value === questionId ? null : questionId;
}

function formatDate(value) {
  if (!value) return '';
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(new Date(value));
}
</script>

<template>
  <LayoutShell>
    <section class="page favorites-page">
      <header class="favorites-hero">
        <div class="favorites-title">
          <span class="favorites-mark"><AppIcon name="star" /></span>
          <div>
            <p class="favorites-kicker">QUESTION COLLECTION</p>
            <h1>收藏题库</h1>
            <p>集中回看笔试中值得复习的题目，按题型快速定位知识盲区。</p>
          </div>
        </div>
        <div class="collection-stat">
          <strong>{{ favorites.length }}</strong>
          <span>道收藏题目</span>
          <small>持续复习，逐个掌握</small>
        </div>
      </header>

      <section v-if="favorites.length" class="favorites-tools" aria-label="收藏题目筛选">
        <div class="type-filters">
          <button
            v-for="filter in typeFilters"
            :key="filter.value"
            type="button"
            :class="{ active: activeType === filter.value }"
            @click="activeType = filter.value"
          >
            {{ filter.label }} <span>{{ filterCount(filter.value) }}</span>
          </button>
        </div>
        <label class="favorite-search">
          <span class="search-icon" aria-hidden="true"></span>
          <input v-model="keyword" type="search" placeholder="搜索题干或题目编号" />
        </label>
      </section>

      <div v-if="loading" class="favorite-loading" aria-label="正在加载收藏题目"><i></i><i></i><i></i></div>
      <p v-if="error" class="form-error">{{ error }}</p>

      <div v-if="!loading && filteredFavorites.length" class="favorite-list">
        <div class="favorite-list-head" aria-hidden="true">
          <span>序号</span><span>题型</span><span>题目内容</span><span>收藏日期</span><span></span>
        </div>
        <article
          v-for="(item, index) in filteredFavorites"
          :key="item.favorite_id"
          class="favorite-item"
          :class="[{ expanded: expandedId === item.question_id }, `type-${item.question_type}`]"
        >
          <button
            class="favorite-row"
            type="button"
            :aria-expanded="expandedId === item.question_id"
            :aria-controls="`favorite-detail-${item.favorite_id}`"
            @click="toggle(item.question_id)"
          >
            <span class="favorite-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="favorite-type">{{ typeLabels[item.question_type] || '题目' }}</span>
            <span class="favorite-copy">
              <strong>{{ item.content }}</strong>
              <small>{{ item.question?.options?.length ? `${item.question.options.length} 个选项` : item.question_type === 'true_false' ? '判断正误' : '主观作答' }}</small>
            </span>
            <time>{{ formatDate(item.created_at) }}</time>
            <span class="favorite-open" :aria-label="expandedId === item.question_id ? '收起题目' : '查看题目'"><i>›</i></span>
          </button>

          <div
            v-if="expandedId === item.question_id"
            :id="`favorite-detail-${item.favorite_id}`"
            class="favorite-detail"
          >
            <div class="detail-heading">
              <div><span>QUESTION DETAIL</span><h2>题目详情</h2></div>
              <small>{{ typeLabels[item.question_type] }} · {{ item.question_id }}</small>
            </div>
            <div v-if="item.question?.options?.length" class="favorite-options">
              <div v-for="option in item.question.options" :key="option.key">
                <b>{{ option.key }}</b><span>{{ option.text }}</span>
              </div>
            </div>
            <p v-else class="favorite-answer-hint">
              {{ item.question_type === 'true_false' ? '请判断上述说法是否正确。' : '请根据题意作答。' }}
            </p>
            <footer>
              <span>该题来自你的真实笔试练习记录</span>
              <button class="remove-favorite" type="button" @click="remove(item.question_id)"><AppIcon name="star" />取消收藏</button>
            </footer>
          </div>
        </article>
      </div>

      <div v-if="!loading && favorites.length === 0" class="favorite-empty">
        <span><AppIcon name="star" /></span>
        <h2>还没有收藏题目</h2>
        <p>进入笔试练习，遇到值得复习的题目时点击“收藏”，它就会出现在这里。</p>
        <RouterLink class="primary-button" to="/study-plan">去笔试练习</RouterLink>
      </div>

      <div v-else-if="!loading && filteredFavorites.length === 0" class="favorite-empty compact">
        <span class="empty-search"><i></i></span>
        <h2>没有找到匹配题目</h2>
        <p>尝试更换题型，或者使用其他关键词搜索。</p>
        <button type="button" class="clear-filter" @click="activeType = 'all'; keyword = ''">清除筛选</button>
      </div>
    </section>
  </LayoutShell>
</template>

<style scoped>
.favorites-page { max-width: 1160px; }
.favorites-hero { position: relative; display: flex; min-height: 190px; align-items: center; justify-content: space-between; gap: 40px; overflow: hidden; margin-bottom: 24px; border: 1px solid #dce5f2; border-radius: 20px; padding: 34px 38px; background: linear-gradient(125deg,#fff 0%,#f5f9ff 58%,#edf4ff 100%); box-shadow: 0 14px 38px rgba(35,68,120,.07); }
.favorites-hero:after { content: ''; position: absolute; right: 130px; top: -85px; width: 220px; height: 220px; border: 38px solid rgba(38,105,207,.045); border-radius: 50%; }
.favorites-title { position: relative; display: flex; align-items: center; gap: 22px; z-index: 1; }
.favorites-mark { display: grid; flex: 0 0 64px; height: 64px; place-items: center; border-radius: 18px; color: #fff; background: linear-gradient(145deg,#3379e8,#175ecb); box-shadow: 0 12px 25px rgba(31,101,211,.25); }
.favorites-mark svg { width: 29px; height: 29px; fill: rgba(255,255,255,.16); }
.favorites-kicker { margin: 0 0 7px!important; color: #2d6ed1!important; font-size: 9px!important; font-weight: 900; letter-spacing: 2.2px; }
.favorites-title h1 { margin: 0; color: #1d2d46; font-family: Georgia,'Songti SC',serif; font-size: 29px; }
.favorites-title > div > p:last-child { max-width: 520px; margin: 9px 0 0; color: #75839a; font-size: 13px; line-height: 1.7; }
.collection-stat { position: relative; display: grid; min-width: 145px; justify-items: end; border-left: 1px solid #d7e2f1; padding-left: 30px; z-index: 1; }
.collection-stat strong { color: #1d5fca; font-family: Georgia,serif; font-size: 42px; line-height: 1; }
.collection-stat span { margin-top: 5px; color: #42526a; font-size: 12px; font-weight: 700; }
.collection-stat small { margin-top: 8px; color: #9aa6b7; font-size: 9px; }
.favorites-tools { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 14px; }
.type-filters { display: flex; min-width: 0; align-items: center; gap: 4px; overflow-x: auto; padding: 3px; }
.type-filters button { display: inline-flex; flex: 0 0 auto; align-items: center; gap: 7px; border: 0; border-radius: 8px; padding: 9px 11px; color: #738097; background: transparent; font-size: 11px; }
.type-filters button:hover { color: #315f9f; background: #f2f6fc; }
.type-filters button.active { color: #1e60c9; background: #eaf2ff; font-weight: 800; }
.type-filters button span { display: grid; min-width: 18px; height: 18px; place-items: center; border-radius: 99px; color: #8995a7; background: #edf1f6; font-size: 9px; }
.type-filters button.active span { color: #fff; background: #2a6fd8; }
.favorite-search { position: relative; flex: 0 0 230px; }
.favorite-search input { width: 100%; height: 38px; border: 1px solid #dce4ef; border-radius: 10px; padding: 0 34px 0 37px; outline: 0; color: #3e4d63; background: #fff; font-size: 11px; }
.favorite-search input:focus { border-color: #8eb1eb; box-shadow: 0 0 0 3px #edf4ff; }
.search-icon { position: absolute; left: 13px; top: 12px; width: 13px; height: 13px; border: 1.5px solid #8c99aa; border-radius: 50%; z-index: 1; }
.search-icon:after { content: ''; position: absolute; right: -5px; bottom: -3px; width: 6px; height: 1.5px; background: #8c99aa; transform: rotate(45deg); }
.favorite-list { overflow: hidden; border: 1px solid #dfe6f0; border-radius: 14px; background: #fff; box-shadow: 0 8px 26px rgba(38,67,112,.05); }
.favorite-list-head,.favorite-row { display: grid; grid-template-columns: 52px 88px minmax(0,1fr) 96px 24px; align-items: center; gap: 16px; }
.favorite-list-head { border-bottom: 1px solid #e6ebf2; padding: 11px 22px; color: #9ba6b6; background: #f8fafd; font-size: 9px; font-weight: 800; letter-spacing: .7px; }
.favorite-item { position: relative; }
.favorite-item:before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: #3d7ee0; opacity: 0; transition: opacity .2s; }
.favorite-item + .favorite-item { border-top: 1px solid #e9edf3; }
.favorite-item.expanded:before { opacity: 1; }
.favorite-item.expanded { background: #fbfdff; }
.favorite-row { width: 100%; border: 0; padding: 19px 22px; color: #26364e; background: transparent; text-align: left; }
.favorite-row:hover { background: #f8fbff; }
.favorite-index { color: #a6b0be; font-family: Georgia,serif; font-size: 14px; }
.favorite-type { justify-self: start; border-radius: 99px; padding: 5px 8px; color: #2c69c6; background: #eaf2ff; font-size: 9px; font-weight: 800; white-space: nowrap; }
.type-multiple_choice .favorite-type { color: #7652bd; background: #f0eaff; }
.type-true_false .favorite-type { color: #218164; background: #e8f7f1; }
.type-short_answer .favorite-type { color: #a66325; background: #fff1df; }
.favorite-copy { display: grid; min-width: 0; gap: 5px; }
.favorite-copy strong { overflow: hidden; color: #314056; font-size: 13px; font-weight: 600; line-height: 1.55; text-overflow: ellipsis; white-space: nowrap; }
.favorite-copy small { color: #a0aaba; font-size: 9px; }
.favorite-row time { color: #8996a9; font-size: 10px; }
.favorite-open { display: grid; place-items: center; color: #6e7c91; }
.favorite-open i { font-size: 21px; font-style: normal; line-height: 1; transition: transform .2s ease; }
.favorite-item.expanded .favorite-open i { color: #2d6fd5; transform: rotate(90deg); }
.favorite-detail { margin: 0 22px 0 74px; border-top: 1px dashed #d9e3ef; padding: 22px 0 24px; }
.detail-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.detail-heading > div { display: grid; gap: 4px; }
.detail-heading span { color: #2d70d5; font-size: 8px; font-weight: 900; letter-spacing: 1.5px; }
.detail-heading h2 { margin: 0; color: #2c3c54; font-size: 14px; }
.detail-heading small { color: #9ba5b4; font-size: 9px; }
.favorite-options { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 9px 12px; }
.favorite-options > div { display: grid; grid-template-columns: 29px minmax(0,1fr); align-items: center; gap: 10px; min-height: 48px; border: 1px solid #e2e8f1; border-radius: 9px; padding: 9px 12px; color: #53627a; background: #fff; font-size: 12px; line-height: 1.55; }
.favorite-options b { display: grid; width: 27px; height: 27px; place-items: center; border-radius: 8px; color: #2b68c5; background: #eaf2ff; font-size: 10px; }
.favorite-answer-hint { margin: 0; border-left: 3px solid #8bb0e8; padding: 12px 15px; color: #65758c; background: #f4f8fd; font-size: 12px; }
.favorite-detail footer { display: flex; align-items: center; gap: 12px; margin-top: 18px; }
.favorite-detail footer > span { flex: 1; color: #a1abba; font-size: 9px; }
.remove-favorite { display: inline-flex; align-items: center; gap: 6px; border: 0; padding: 6px; color: #a55b64; background: transparent; font-size: 10px; }
.remove-favorite svg { width: 13px; height: 13px; fill: #f6dfe2; }
.remove-favorite:hover { color: #d0394d; }
.favorite-loading { display: grid; gap: 1px; overflow: hidden; border: 1px solid #e1e7ef; border-radius: 14px; background: #e8edf3; }
.favorite-loading i { height: 72px; background: linear-gradient(90deg,#f7f9fc 25%,#fff 40%,#f7f9fc 65%); background-size: 300% 100%; animation: loading-shine 1.2s infinite; }
@keyframes loading-shine { to { background-position: -150% 0; } }
.favorite-empty { display: grid; min-height: 360px; align-content: center; justify-items: center; border: 1px dashed #cfdbea; border-radius: 16px; padding: 42px; background: linear-gradient(145deg,#fbfdff,#f5f8fc); text-align: center; }
.favorite-empty > span { display: grid; width: 58px; height: 58px; place-items: center; border-radius: 18px; color: #3b75d0; background: #e9f1ff; }
.favorite-empty > span svg { width: 25px; fill: rgba(48,110,206,.08); }
.favorite-empty h2 { margin: 19px 0 8px; color: #314158; font-size: 17px; }
.favorite-empty p { max-width: 440px; margin: 0 0 22px; color: #8490a2; font-size: 12px; line-height: 1.7; }
.favorite-empty .primary-button { font-size: 11px; }
.favorite-empty.compact { min-height: 280px; }
.empty-search { position: relative; }
.empty-search i { width: 18px; height: 18px; border: 2px solid #4e80cb; border-radius: 50%; }
.empty-search i:after { content: ''; position: absolute; width: 9px; height: 2px; background: #4e80cb; transform: translate(14px,16px) rotate(45deg); }
.clear-filter { border: 0; padding: 7px; color: #2769cc; background: transparent; font-size: 11px; }
@media(max-width:800px){.favorites-hero{align-items:flex-start;padding:28px}.collection-stat{min-width:auto}.favorites-tools{align-items:stretch;flex-direction:column}.favorite-search{flex-basis:auto}.favorite-list-head{display:none}.favorite-row{grid-template-columns:42px 82px minmax(0,1fr) 22px}.favorite-row time{display:none}.favorite-detail{margin-left:64px}.favorite-options{grid-template-columns:1fr}}
@media(max-width:560px){.favorites-hero{min-height:auto;flex-direction:column;gap:24px;padding:24px}.favorites-title{align-items:flex-start}.favorites-mark{flex-basis:48px;height:48px;border-radius:14px}.favorites-mark svg{width:22px}.collection-stat{width:100%;justify-items:start;border-top:1px solid #dbe4f0;border-left:0;padding:18px 0 0}.collection-stat strong{font-size:32px}.favorite-row{grid-template-columns:28px minmax(0,1fr) 20px;gap:10px;padding:16px 14px}.favorite-type{grid-column:2;grid-row:1}.favorite-copy{grid-column:2;grid-row:2}.favorite-open{grid-column:3;grid-row:1/3}.favorite-index{grid-row:1/3}.favorite-detail{margin:0 14px 0 52px}.detail-heading{align-items:flex-start;flex-direction:column}.detail-heading small{word-break:break-all}.favorite-detail footer{align-items:flex-start;flex-direction:column}.favorite-empty{min-height:320px;padding:28px 20px}}
</style>
