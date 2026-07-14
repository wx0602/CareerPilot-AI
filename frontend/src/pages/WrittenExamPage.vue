<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandLogo from '../components/BrandLogo.vue';
import { api, getSession } from '../api/client';
import { QUESTION_MIX, getLearningModule } from '../data/learningModules';

const router = useRouter();
const current = ref(0);
const paper = ref(null);
const answers = ref({});
const favoriteIds = ref(new Set());
const loading = ref(false);
const error = ref('');
const notice = ref('');
const session = ref(null);

const question = computed(() => paper.value?.questions?.[current.value]);
const moduleInfo = computed(() => getLearningModule(session.value?.learning_module));
const questionMix = computed(() => session.value?.question_mix || QUESTION_MIX);
const questionCount = computed(() =>
  Object.values(questionMix.value).reduce((sum, value) => sum + Number(value || 0), 0)
);

const typeLabels = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  short_answer: '简答题'
};
const questionTypeOrder = ['single_choice', 'multiple_choice', 'true_false', 'short_answer'];

const questionGroups = computed(() => {
  const groups = {
    single_choice: [],
    multiple_choice: [],
    true_false: [],
    short_answer: []
  };
  (paper.value?.questions || []).forEach((item, index) => {
    groups[item.question_type]?.push({ ...item, index });
  });
  return groups;
});

const currentTypeLabel = computed(() => typeLabels[question.value?.question_type] || '题目');

onMounted(async () => {
  session.value = getSession();
  await loadExam();
  await loadFavorites();
});

async function loadExam() {
  if (!session.value) {
    router.push('/dashboard');
    return;
  }
  if (!session.value.learning_module) {
    router.push('/study-plan');
    return;
  }

  loading.value = true;
  error.value = '';
  try {
    const generated = await api.generateExam({
      session_id: session.value.session_id,
      position: session.value.position || moduleInfo.value?.position || '技术岗位',
      company: session.value.company,
      difficulty: 'medium',
      question_count: questionCount.value,
      learning_module: session.value.learning_module,
      learning_module_title: session.value.learning_module_title || moduleInfo.value?.title,
      question_mix: questionMix.value
    });
    paper.value = {
      ...generated,
      questions: [...generated.questions].sort(
        (left, right) =>
          questionTypeOrder.indexOf(left.question_type) -
          questionTypeOrder.indexOf(right.question_type)
      )
    };
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

async function loadFavorites() {
  try {
    const rows = await api.listFavorites();
    favoriteIds.value = new Set(rows.map((item) => item.question_id));
  } catch {
    favoriteIds.value = new Set();
  }
}

function setAnswer(q, value, checked) {
  if (q.question_type === 'multiple_choice') {
    const old = Array.isArray(answers.value[q.question_id]) ? answers.value[q.question_id] : [];
    answers.value[q.question_id] = checked
      ? [...new Set([...old, value])]
      : old.filter((item) => item !== value);
    return;
  }
  answers.value[q.question_id] = value;
}

async function favoriteCurrent() {
  if (!question.value) return;
  notice.value = '';
  error.value = '';
  try {
    await api.addFavorite(question.value);
    favoriteIds.value = new Set([...favoriteIds.value, question.value.question_id]);
    notice.value = '已收藏到题库';
  } catch (err) {
    error.value = err.message;
  }
}

async function submit() {
  if (!paper.value) return;
  loading.value = true;
  error.value = '';
  try {
    const payloadAnswers = paper.value.questions.map((q) => ({
      question_id: q.question_id,
      answer: answers.value[q.question_id] ?? (q.question_type === 'multiple_choice' ? [] : '')
    }));
    await api.submitExam({
      session_id: paper.value.session_id,
      exam_id: paper.value.exam_id,
      answers: payloadAnswers
    });
    router.push('/interview');
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="exam-page">
    <header class="exam-topbar">
      <BrandLogo />
      <button class="back-link" @click="router.push('/dashboard')">
        <AppIcon name="back" />返回
      </button>
      <h1>{{ paper?.title || `${session?.learning_module_title || '学习模块'} 练习` }}</h1>
      <span class="timer">
        <AppIcon name="clock" />固定配比 {{ questionCount }} 题
      </span>
      <button class="primary-button submit-small" :disabled="loading || !paper" @click="submit">
        交卷
      </button>
    </header>

    <div class="exam-summary">
      <span>{{ session?.learning_module_title || '未命名模块' }}</span>
      <b>{{ questionMix.single_choice }} 单选</b>
      <b>{{ questionMix.multiple_choice }} 多选</b>
      <b>{{ questionMix.true_false }} 判断</b>
      <b>{{ questionMix.short_answer }} 简答</b>
    </div>

    <p v-if="loading" class="privacy-note">正在生成练习题...</p>
    <p v-if="notice" class="privacy-note">{{ notice }}</p>
    <p v-if="error" class="form-error">{{ error }}</p>

    <div v-if="paper && question" class="exam-layout">
      <aside class="question-nav">
        <h2>题目导航</h2>
        <section v-for="(items, type) in questionGroups" :key="type">
          <b>{{ typeLabels[type] }} ({{ items.length }})</b>
          <div>
            <button
              v-for="item in items"
              :key="item.question_id"
              :class="{ active: current === item.index, done: answers[item.question_id] !== undefined }"
              @click="current = item.index"
            >
              {{ item.index + 1 }}
            </button>
          </div>
        </section>
      </aside>

      <section class="question-panel">
        <div class="question-meta">
          <b>{{ currentTypeLabel }} {{ current + 1 }}/{{ paper.questions.length }}</b>
          <span>{{ session?.learning_module_title }} 模块练习</span>
        </div>
        <h2>{{ question.content }}</h2>

        <template v-if="question.question_type === 'short_answer'">
          <textarea
            class="answer-input"
            :value="answers[question.question_id] || ''"
            placeholder="请输入你的简答题答案"
            @input="setAnswer(question, $event.target.value)"
          ></textarea>
        </template>

        <template v-else>
          <label
            v-for="option in question.options"
            :key="option.key"
            class="option-row"
            :class="{
              selected: question.question_type === 'multiple_choice'
                ? (answers[question.question_id] || []).includes(option.key)
                : answers[question.question_id] === option.key
            }"
          >
            <input
              v-if="question.question_type === 'multiple_choice'"
              type="checkbox"
              :checked="(answers[question.question_id] || []).includes(option.key)"
              @change="setAnswer(question, option.key, $event.target.checked)"
            />
            <input
              v-else
              type="radio"
              :name="question.question_id"
              :checked="answers[question.question_id] === option.key"
              @change="setAnswer(question, option.key)"
            />
            <b>{{ option.key }}.</b>
            <span>{{ option.text }}</span>
          </label>

          <label
            v-if="question.question_type === 'true_false'"
            class="option-row"
            :class="{ selected: answers[question.question_id] === 'true' }"
          >
            <input
              type="radio"
              :name="question.question_id"
              :checked="answers[question.question_id] === 'true'"
              @change="setAnswer(question, 'true')"
            />
            正确
          </label>

          <label
            v-if="question.question_type === 'true_false'"
            class="option-row"
            :class="{ selected: answers[question.question_id] === 'false' }"
          >
            <input
              type="radio"
              :name="question.question_id"
              :checked="answers[question.question_id] === 'false'"
              @change="setAnswer(question, 'false')"
            />
            错误
          </label>
        </template>

        <div class="question-actions">
          <button class="ghost-button" @click="favoriteCurrent">
            {{ favoriteIds.has(question.question_id) ? '已收藏' : '收藏' }}
          </button>
          <span></span>
          <button class="ghost-button" :disabled="current === 0" @click="current--">上一题</button>
          <button class="primary-button" @click="current === paper.questions.length - 1 ? submit() : current++">
            {{ current === paper.questions.length - 1 ? '完成练习' : '下一题' }}
          </button>
        </div>
      </section>
    </div>
  </main>
</template>
