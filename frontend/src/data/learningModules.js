export const QUESTION_MIX = {
  single_choice: 5,
  multiple_choice: 2,
  true_false: 5,
  short_answer: 3
};

export const QUESTION_MIX_LABEL = '5 单选 + 2 多选 + 5 判断 + 3 简答';

export const learningModules = [
  {
    id: 'java_backend',
    title: 'Java 后端',
    category: '后端基础',
    summary: '集合、并发、JVM、Spring、MySQL 等',
    position: 'Java 后端工程师',
    available: true
  },
  {
    id: 'python_backend',
    title: 'Python 后端',
    category: '后端基础',
    summary: 'Python、异步、FastAPI、Django、ORM 等',
    position: 'Python 后端工程师',
    available: true
  },
  {
    id: 'frontend_javascript',
    title: 'JavaScript',
    category: '前端基础',
    summary: '语言基础、闭包、原型、异步模型',
    position: '前端工程师',
    available: true
  },
  {
    id: 'frontend_typescript',
    title: 'TypeScript',
    category: '前端基础',
    summary: '类型系统、泛型、声明文件、工程约束',
    position: '前端工程师',
    available: true
  },
  {
    id: 'frontend_vue',
    title: 'Vue',
    category: '前端基础',
    summary: '响应式、组件通信、路由、状态管理',
    position: '前端工程师',
    available: true
  },
  {
    id: 'browser_principles',
    title: '浏览器原理',
    category: '前端基础',
    summary: '渲染流程、事件循环、缓存、同源策略',
    position: '前端工程师',
    available: true
  },
  {
    id: 'go_backend',
    title: 'Go 后端',
    category: '语言方向',
    summary: 'goroutine、channel、内存模型、服务开发',
    position: 'Go 后端工程师',
    available: true
  },
  {
    id: 'cpp_basic',
    title: 'C++ 基础',
    category: '语言方向',
    summary: '对象模型、STL、内存管理、现代 C++',
    position: 'C++ 工程师',
    available: true
  },
  {
    id: 'ai_llm_engineering',
    title: 'AI / LLM 工程',
    category: 'AI 方向',
    summary: 'Prompt、RAG、向量检索、Agent、评测',
    position: 'AI 工程师',
    available: true
  },
  {
    id: 'product_manager',
    title: '产品',
    category: '通用岗位',
    summary: '需求分析、优先级、指标、方案表达',
    position: '产品经理',
    available: true
  },
  {
    id: 'testing_engineering',
    title: '测试',
    category: '通用岗位',
    summary: '测试设计、接口测试、自动化、缺陷分析',
    position: '测试工程师',
    available: true
  },
  {
    id: 'devops_engineering',
    title: '运维',
    category: '通用岗位',
    summary: 'Linux、网络、监控、发布、故障处理',
    position: '运维工程师',
    available: true
  }
];

export function getLearningModule(moduleId) {
  return learningModules.find((item) => item.id === moduleId) || null;
}
