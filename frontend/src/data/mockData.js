export const scenarios = [
  { icon: '▣', tone: 'blue', title: '企业笔试', desc: '真题训练 · 智能评估', note: '适合技术类岗位', route: '/exam', ready: true },
  { icon: '●', tone: 'green', title: '文本面试', desc: 'AI 模拟面试 · 实时对话', note: '适合各类岗位', route: '/interview', ready: true },
  { icon: '♟', tone: 'purple', title: '群体面试', desc: '多人协作 · 角色扮演', note: '适合管理类岗位', ready: false },
  { icon: 'ϟ', tone: 'violet', title: '压力面试', desc: '高强问答 · 抗压训练', note: '适合高强度岗位', ready: false },
  { icon: '★', tone: 'orange', title: '行为面试', desc: 'STAR 法则 · 行为追问', note: '适合各类岗位', route: '/interview', ready: true },
  { icon: '◎', tone: 'indigo', title: '职业规划', desc: '职业发展 · 方向探索', note: '适合求职规划', ready: false }
];

export const questions = [
  { id: 1, stem: '以下关于 TCP 和 UDP 的说法中，正确的是？', options: ['TCP 是无连接的，UDP 是面向连接的', 'TCP 提供可靠的、面向连接的服务', 'UDP 提供可靠的、面向连接的服务', 'TCP 和 UDP 都是应用层协议'], answer: 1 },
  { id: 2, stem: 'Vue 3 中用于声明响应式基本类型数据的 API 是？', options: ['watch', 'ref', 'provide', 'defineProps'], answer: 1 },
  { id: 3, stem: 'HTTP 状态码 404 表示什么？', options: ['请求成功', '服务器错误', '资源未找到', '无权限'], answer: 2 }
];

export const report = {
  overall_score: 86,
  dimension_scores: { 专业知识: 90, 问题解决: 80, 沟通表达: 85, 逻辑思维: 88, 学习能力: 82 },
  weaknesses: ['高压场景下回答完整度', '系统设计中的深度分析', '复杂问题的结构化拆解'],
  suggestions: ['重点复习后端系统设计', '使用 STAR 法则组织项目经历', '进行限时模拟面试训练']
};
