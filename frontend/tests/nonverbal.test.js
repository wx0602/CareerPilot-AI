import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createNonverbalAnalyzer,
  createQuestionMetrics,
  recordFaceObservation,
  recordPoseObservation
} from '../src/services/nonverbalAnalyzer.js';
import { scoreNonverbal } from '../src/services/nonverbalScorer.js';

function createIdealQuestion({ inputMode = 'text', durationMs = 10000 } = {}) {
  const question = createQuestionMetrics('question-1', {
    inputMode,
    presentedAt: 1000,
    answerStartedAt: 3000
  });
  question.durationMs = durationMs;
  question.responseDelayMs = 2000;
  for (let index = 0; index < 25; index += 1) {
    recordFaceObservation(question, {
      detected: true,
      headDeviation: false,
      headTilt: false,
      facialDynamic: index % 3 === 0,
      mouthMeasured: true,
      mouthDynamic: index % 4 === 0
    }, index * 300);
  }
  for (let index = 0; index < 12; index += 1) {
    recordPoseObservation(question, {
      detected: true,
      shoulderTilt: false,
      bodyOffset: false,
      excessiveMovement: false
    }, index * 600);
  }
  return question;
}

test('理想样本的五维评分和总分均处于 0 到 100', () => {
  const result = scoreNonverbal([createIdealQuestion()]);
  assert.equal(result.status, 'complete');
  assert.ok(result.total_score >= 0 && result.total_score <= 100);
  assert.equal(Object.keys(result.dimensions).length, 5);
  for (const score of Object.values(result.dimensions)) {
    assert.ok(score >= 0 && score <= 100);
  }
});

test('连续约两秒无人脸才产生离开画面事件', () => {
  const question = createQuestionMetrics('no-face');
  recordFaceObservation(question, { detected: false }, 0);
  recordFaceObservation(question, { detected: false }, 1000);
  recordFaceObservation(question, { detected: false }, 2100);
  assert.equal(question.noFaceEvents, 1);
});

test('单帧无人脸后恢复不会产生离开画面事件', () => {
  const question = createQuestionMetrics('single-miss');
  recordFaceObservation(question, { detected: false }, 0);
  recordFaceObservation(question, { detected: true }, 300);
  assert.equal(question.noFaceEvents, 0);
});

test('持续低头或转头约三秒产生头部偏离事件', () => {
  const question = createQuestionMetrics('head-away');
  const observation = { detected: true, headDeviation: true, headTilt: false };
  recordFaceObservation(question, observation, 0);
  recordFaceObservation(question, observation, 1500);
  recordFaceObservation(question, observation, 3100);
  assert.equal(question.headDeviationEvents, 1);
});

test('文字回答不因嘴部没有动态而扣分', () => {
  const stillMouth = createIdealQuestion({ inputMode: 'text' });
  stillMouth.mouthDynamicSamples = 0;
  const movingMouth = { ...stillMouth, mouthDynamicSamples: stillMouth.mouthSamples };
  const stillScore = scoreNonverbal([stillMouth]);
  const movingScore = scoreNonverbal([movingMouth]);
  assert.equal(stillScore.dimensions.facial_dynamics, movingScore.dimensions.facial_dynamics);
  assert.equal(stillScore.total_score, movingScore.total_score);
});

test('总有效分析时间不足返回明确的数据不足结果', () => {
  const result = scoreNonverbal([createIdealQuestion({ durationMs: 7900 })]);
  assert.equal(result.status, 'insufficient_data');
  assert.equal(result.reason, 'answer_too_short');
  assert.equal(result.total_score, null);
});

test('同一道题重复开始不会清空或重复完成本题数据', async () => {
  const originalDocument = globalThis.document;
  globalThis.document = {
    visibilityState: 'visible',
    createElement: () => ({
      width: 0,
      height: 0,
      getContext: () => ({ drawImage() {} })
    }),
    addEventListener() {},
    removeEventListener() {}
  };
  const detector = { close() {}, detectForVideo() { return {}; } };
  const analyzer = createNonverbalAnalyzer({
    detectorFactory: async () => ({ faceLandmarker: detector, poseLandmarker: detector })
  });
  try {
    await analyzer.initialize({ readyState: 0, videoWidth: 0 });
    assert.equal(analyzer.startQuestion('same-question', { answerStartedAt: 1000 }), true);
    assert.equal(analyzer.startQuestion('same-question', { answerStartedAt: 9999 }), true);
    const first = analyzer.finishQuestion({ questionId: 'same-question', submittedAt: 12000 });
    const repeated = analyzer.finishQuestion({ questionId: 'same-question', submittedAt: 15000 });
    assert.equal(first.answerStartedAt, 1000);
    assert.deepEqual(repeated, first);
  } finally {
    analyzer.destroy();
    globalThis.document = originalDocument;
  }
});
