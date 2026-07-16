<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import LayoutShell from '../components/LayoutShell.vue';
import AppIcon from '../components/AppIcon.vue';

const route = useRoute();
const router = useRouter();

const scenes = {
  written: {
    eyebrow: 'WRITTEN ASSESSMENT',
    code: '01 / KNOWLEDGE',
    title: '企业笔试',
    headline: '选择目标企业，完成对应岗位真实套题',
    description: '进入企业后选择应聘岗位，系统按牛客题库中的实际题型生成完整试卷，交卷后直接生成专项报告。',
    action: '选择企业与岗位',
    target: '/company-exams',
    tone: 'blue',
    stats: [['企业', '真实分类'], ['岗位', '独立套题'], ['自动', '评分报告']],
    steps: ['选择目标企业', '选择应聘岗位并答题', '查看专项能力报告'],
    note: '笔试与面试相互独立，不会在交卷后跳转面试。'
  },
  'text-interview': {
    eyebrow: 'TEXT INTERVIEW',
    code: '02 / DIALOGUE',
    title: '文本面试',
    headline: '把经历讲具体，让每次追问都有依据',
    description: '可上传简历或岗位描述，AI 面试官会结合材料进行文字提问、回答评价和针对性追问。',
    action: '准备面试材料',
    target: '/upload',
    tone: 'green',
    stats: [['实时', '文字对话'], ['多轮', '针对追问'], ['自动', '保存报告']],
    steps: ['上传简历或 JD', '进行多轮问答', '结束并保存报告'],
    note: '材料只服务于面试，不参与企业笔试组卷。'
  },
  group: {
    eyebrow: 'GROUP ASSESSMENT',
    code: '03 / COLLABORATION',
    title: '群体面试',
    headline: '用观点推动讨论，而不是抢占发言',
    description: '你将与逻辑分析型、协调合作型和质疑挑战型三名 AI 候选人共同完成一场文字版无领导小组讨论。',
    action: '进入群体讨论',
    target: '/simulation-interview?autostart=1',
    tone: 'purple',
    stats: [['5', '讨论角色'], ['7', '完整阶段'], ['8', '评分维度']],
    steps: ['理解案例并陈述', '讨论分歧与共识', '总结并生成报告'],
    note: 'AI 候选人会相互回应，面试官只负责案例介绍和流程推进。'
  },
  stress: {
    eyebrow: 'PRESSURE PRACTICE',
    code: '04 / RESILIENCE',
    title: '压力面试',
    headline: '在连续质疑中保持直接、可信和稳定',
    description: '面试官会针对空泛、缺少数据、前后矛盾、回避问题和个人贡献不清进行安全、专业的文字追问。',
    action: '开始压力面试',
    target: '/simulation-interview?autostart=1',
    tone: 'coral',
    stats: [['3', '压力等级'], ['即时', '动态调整'], ['8', '评分维度']],
    steps: ['选择初始压力', '回应连续追问', '结束并生成报告'],
    note: '随时输入“停止”“暂停”或“降低压力”，系统会立即响应。'
  },
  pitch: {
    eyebrow: 'PITCH DEFENSE',
    code: '05 / BUSINESS',
    title: '路演答辩',
    headline: '从商业假设到落地路径，接受完整质询',
    description: 'AI 评委围绕市场价值、商业逻辑、可行性、创新性和表达能力提出问题并持续追问。',
    action: '开始路演答辩',
    target: '/upload?flow=pitch',
    tone: 'orange',
    stats: [['5', '核心维度'], ['AI', '评委追问'], ['结构化', '答辩报告']],
    steps: ['陈述项目背景', '回应评委质询', '获得改进建议'],
    note: '建议在开始前准备项目定位、目标用户、商业模式和关键数据。'
  },
  career: {
    eyebrow: 'CAREER DISCOVERY',
    code: '06 / DIRECTION',
    title: '职业规划',
    headline: '先理解自己，再选择值得投入的方向',
    description: '从 MBTI、霍兰德职业兴趣等测评入口开始，逐步形成职业倾向、岗位匹配和发展建议。',
    action: '选择职业测评',
    target: '/career-assessment',
    tone: 'indigo',
    stats: [['多种', '测评入口'], ['清晰', '特质分析'], ['个性化', '职业方向']],
    steps: ['选择测评工具', '完成外部测评', '查看职业方向说明'],
    note: '职业测评用于自我探索，不替代专业心理诊断或唯一职业决策。'
  }
};

const scene = computed(() => scenes[route.params.sceneId]);

function enterScene() {
  if (!scene.value) {
    router.replace('/dashboard');
    return;
  }
  router.push(scene.value.target);
}
</script>

<template>
  <LayoutShell>
    <main v-if="scene" class="scene-intro" :class="`tone-${scene.tone}`">
      <header class="scene-nav">
        <button class="back-link" @click="router.push('/dashboard')"><AppIcon name="back" />返回场景</button>
        <span>{{ scene.code }}</span>
      </header>

      <section class="scene-card">
        <div class="scene-copy">
          <span class="scene-eyebrow">{{ scene.eyebrow }}</span>
          <h1>{{ scene.headline }}</h1>
          <p>{{ scene.description }}</p>

          <div class="scene-stats">
            <article v-for="item in scene.stats" :key="item[1]"><b>{{ item[0] }}</b><span>{{ item[1] }}</span></article>
          </div>

          <button class="scene-action" @click="enterScene">{{ scene.action }}<AppIcon name="arrow" /></button>
          <small>{{ scene.note }}</small>
        </div>

        <aside class="scene-panel">
          <div class="scene-number">{{ scene.code.split(' / ')[0] }}</div>
          <div class="scene-title"><span>TRAINING SCENE</span><h2>{{ scene.title }}</h2></div>
          <ol>
            <li v-for="(step, index) in scene.steps" :key="step"><b>0{{ index + 1 }}</b><span>{{ step }}</span></li>
          </ol>
          <div class="scene-orbit" aria-hidden="true"><i></i><i></i><i></i></div>
        </aside>
      </section>
    </main>
    <main v-else class="scene-missing">场景不存在，正在返回...</main>
  </LayoutShell>
</template>

<style scoped>
.scene-intro {
  --accent: #2d6ed2;
  --accent-soft: #dce9fb;
  --ink: #172b4a;
  min-height: 100vh;
  padding: 34px;
  color: var(--ink);
  background:
    radial-gradient(circle at 85% 8%, var(--accent-soft), transparent 30%),
    linear-gradient(135deg, #f3f6fa, #eef2f6);
}
.tone-green { --accent: #238367; --accent-soft: #d9eee6; --ink: #153b32; }
.tone-purple { --accent: #7b4eae; --accent-soft: #eee4f6; --ink: #38234f; }
.tone-coral { --accent: #bd554e; --accent-soft: #f8e3df; --ink: #512826; }
.tone-orange { --accent: #b9622f; --accent-soft: #f4dfd1; --ink: #4a2c1d; }
.tone-indigo { --accent: #4558a8; --accent-soft: #dfe3f5; --ink: #202c62; }
.scene-nav { display: flex; max-width: 1080px; align-items: center; justify-content: space-between; margin: 0 auto 28px; }
.scene-nav > span { color: var(--accent); font-size: 10px; font-weight: 900; letter-spacing: 2px; }
.scene-card { display: grid; grid-template-columns: 1.1fr .9fr; max-width: 1080px; min-height: 570px; margin: auto; overflow: hidden; border: 1px solid rgba(36,55,82,.1); border-radius: 28px; background: rgba(255,255,255,.9); box-shadow: 0 24px 80px rgba(30,49,74,.11); }
.scene-copy { display: flex; align-items: flex-start; flex-direction: column; justify-content: center; padding: 70px; }
.scene-eyebrow { color: var(--accent); font-size: 10px; font-weight: 900; letter-spacing: 2.5px; }
.scene-copy h1 { display: -webkit-box; max-width: 620px; min-height: 2.5em; margin: 18px 0; overflow: hidden; font-family: Georgia, 'Songti SC', serif; font-size: clamp(30px, 4vw, 48px); font-weight: 600; line-height: 1.25; letter-spacing: -.6px; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.scene-copy > p { max-width: 650px; margin: 0; color: #6d7c91; font-size: 14px; line-height: 1.9; }
.scene-stats { display: grid; width: 100%; grid-template-columns: repeat(3, 1fr); margin: 35px 0; border-top: 1px solid #e4e9ef; border-bottom: 1px solid #e4e9ef; }
.scene-stats article { display: grid; gap: 4px; padding: 20px 10px 20px 0; }
.scene-stats article + article { border-left: 1px solid #e4e9ef; padding-left: 20px; }
.scene-stats b { color: var(--accent); font-family: Georgia, serif; font-size: 22px; }
.scene-stats span { color: #8995a5; font-size: 10px; }
.scene-action { display: flex; align-items: center; gap: 30px; border: 0; border-radius: 11px; padding: 14px 20px; color: #fff; background: var(--accent); box-shadow: 0 12px 30px color-mix(in srgb, var(--accent) 28%, transparent); font-size: 12px; font-weight: 800; }
.scene-action :deep(svg) { width: 15px; }
.scene-copy > small { max-width: 540px; margin-top: 16px; color: #9aa4b2; font-size: 10px; line-height: 1.6; }
.scene-panel { position: relative; display: flex; overflow: hidden; flex-direction: column; justify-content: flex-end; padding: 50px; color: #fff; background: var(--ink); isolation: isolate; }
.scene-number { position: absolute; top: 22px; right: 34px; color: rgba(255,255,255,.06); font-family: Georgia, serif; font-size: 180px; line-height: 1; }
.scene-title { position: absolute; top: 50px; left: 52px; z-index: 2; }
.scene-title span { color: color-mix(in srgb, var(--accent) 65%, white); font-size: 9px; font-weight: 900; letter-spacing: 2px; }
.scene-title h2 { margin: 8px 0 0; font-family: Georgia, 'Songti SC', serif; font-size: 30px; }
.scene-panel ol { position: relative; z-index: 2; margin: 0; padding: 0; list-style: none; }
.scene-panel li { display: flex; align-items: center; gap: 17px; border-top: 1px solid rgba(255,255,255,.14); padding: 20px 0; }
.scene-panel li b { color: color-mix(in srgb, var(--accent) 65%, white); font-family: Georgia, serif; font-size: 12px; }
.scene-panel li span { font-size: 12px; }
.scene-orbit { position: absolute; top: 32%; left: 50%; width: 280px; height: 280px; transform: translate(-50%,-50%); border: 1px solid rgba(255,255,255,.08); border-radius: 50%; }
.scene-orbit i { position: absolute; inset: 38px; border: 1px solid rgba(255,255,255,.07); border-radius: 50%; }.scene-orbit i:nth-child(2){inset:75px}.scene-orbit i:nth-child(3){inset:112px;background:var(--accent);box-shadow:0 0 55px color-mix(in srgb,var(--accent) 60%,transparent)}
.scene-missing { display: grid; min-height: 100vh; place-items: center; color: #718096; background: #f3f6fa; }
@media(max-width:900px){.scene-intro{padding:20px 12px}.scene-card{grid-template-columns:1fr}.scene-copy{padding:45px 30px}.scene-panel{min-height:480px;padding:38px 30px}.scene-title{top:38px;left:30px}.scene-stats{grid-template-columns:1fr}.scene-stats article+.scene-stats article{border-top:1px solid #e4e9ef;border-left:0;padding-left:0}.scene-copy h1{font-size:38px}}
</style>
