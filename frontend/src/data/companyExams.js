export const companyExams = [
  {
    id: 'alibaba',
    name: '阿里巴巴',
    description: '研发、算法与数据岗位专项笔试',
    positions: [
      {
        id: 'engineering',
        title: '研发岗',
        summary: '编程基础、算法、操作系统、网络与数据库',
        questionMix: {
          single_choice: 8,
          multiple_choice: 7,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'algorithm',
        title: '算法岗',
        summary: '数据结构、机器学习、概率统计与算法应用',
        questionMix: {
          single_choice: 10,
          multiple_choice: 7,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'data_engineering',
        title: '数据岗',
        summary: 'SQL、数据仓库、数据分析与数据工程',
        questionMix: {
          single_choice: 15,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 3
        }
      }
    ]
  },
  {
    id: 'jd',
    name: '京东',
    description: '算法、前端与测试岗位专项笔试',
    positions: [
      {
        id: 'algorithm',
        title: '算法岗',
        summary: '数据结构、算法设计、机器学习与工程应用',
        questionMix: {
          single_choice: 20,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'frontend',
        title: '前端岗',
        summary: 'JavaScript、浏览器原理、网络与前端工程化',
        questionMix: {
          single_choice: 22,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'testing',
        title: '测试岗',
        summary: '测试理论、用例设计、自动化测试与质量保障',
        questionMix: {
          single_choice: 20,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 3
        }
      }
    ]
  },
  {
    id: 'meituan',
    name: '美团',
    description: '算法、全栈与测试岗位专项笔试',
    positions: [
      {
        id: 'algorithm',
        title: '算法岗',
        summary: '数据结构、算法设计、机器学习与业务场景应用',
        questionMix: {
          single_choice: 8,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 4
        }
      },
      {
        id: 'fullstack',
        title: '全栈岗',
        summary: '前后端基础、网络、数据库与工程实践',
        questionMix: {
          single_choice: 10,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'testing',
        title: '测试岗',
        summary: '测试理论、用例设计、自动化测试与质量保障',
        questionMix: {
          single_choice: 15,
          multiple_choice: 0,
          true_false: 0,
          short_answer: 3
        }
      }
    ]
  },
  {
    id: 'xiaohongshu',
    name: '小红书',
    description: '数据、前端与算法岗位专项笔试',
    positions: [
      {
        id: 'data_engineering',
        title: '数据岗',
        summary: 'SQL、数据分析、数据仓库与数据工程实践',
        questionMix: {
          single_choice: 15,
          multiple_choice: 5,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'frontend',
        title: '前端岗',
        summary: 'JavaScript、浏览器原理、网络与前端工程化',
        questionMix: {
          single_choice: 15,
          multiple_choice: 5,
          true_false: 0,
          short_answer: 3
        }
      },
      {
        id: 'algorithm',
        title: '算法岗',
        summary: '数据结构、算法设计、机器学习与推荐场景应用',
        questionMix: {
          single_choice: 15,
          multiple_choice: 7,
          true_false: 0,
          short_answer: 3
        }
      }
    ]
  },
  {
    id: 'xiaomi',
    name: '小米',
    description: '测试、算法与前端岗位专项笔试',
    positions: [
      {
        id: 'testing',
        title: '测试岗',
        summary: '测试理论、用例设计、自动化测试与质量保障',
        questionMix: {
          single_choice: 10,
          multiple_choice: 10,
          true_false: 0,
          short_answer: 2
        }
      },
      {
        id: 'algorithm',
        title: '算法岗',
        summary: '数据结构、算法设计、机器学习与工程应用',
        questionMix: {
          single_choice: 12,
          multiple_choice: 8,
          true_false: 0,
          short_answer: 2
        }
      },
      {
        id: 'frontend',
        title: '前端岗',
        summary: 'JavaScript、浏览器原理、网络与前端工程化',
        questionMix: {
          single_choice: 10,
          multiple_choice: 10,
          true_false: 0,
          short_answer: 2
        }
      }
    ]
  }
];

export function getCompany(companyId) {
  return companyExams.find((item) => item.id === companyId) || null;
}

export function getCompanyPosition(companyId, positionId) {
  return getCompany(companyId)?.positions.find((item) => item.id === positionId) || null;
}
