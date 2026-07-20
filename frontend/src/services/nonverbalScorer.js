export const NONVERBAL_DIMENSION_LABELS = Object.freeze({
  camera_attention: '镜头关注度',
  body_posture: '身体姿态',
  movement_stability: '动作稳定性',
  interaction_state: '互动状态',
  facial_dynamics: '面部动态自然度'
});

const REASON_MESSAGES = Object.freeze({
  camera_denied: '摄像头未授权，本次未生成非语言表现评分。',
  camera_disabled: '摄像头未开启，本次未生成非语言表现评分。',
  model_load_failed: '视觉分析模型加载失败，本次未生成非语言表现评分。',
  answer_too_short: '有效回答视频时间过短，本次未生成可靠的非语言表现评分。',
  insufficient_face_samples: '有效人脸样本不足，本次未生成可靠的非语言表现评分。',
  analysis_error: '视觉分析运行异常，本次未生成非语言表现评分。'
});

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Number(value) || 0));
}

function ratio(part, total, fallback = 0) {
  return total > 0 ? clamp(part / total, 0, 1) : fallback;
}

function rounded(value) {
  return Math.round(clamp(value));
}

function roundedSeconds(milliseconds) {
  return Math.round((Math.max(0, milliseconds) / 1000) * 10) / 10;
}

export function createInsufficientResult(reason, statistics = {}) {
  const safeReason = REASON_MESSAGES[reason] ? reason : 'analysis_error';
  return {
    status: 'insufficient_data',
    reason: safeReason,
    message: REASON_MESSAGES[safeReason],
    total_score: null,
    dimensions: null,
    statistics,
    strengths: [],
    suggestions: []
  };
}

function aggregateQuestionResults(questionResults) {
  const aggregate = {
    questionCount: questionResults.length,
    sampleCount: 0,
    validFaceSamples: 0,
    faceDetectionSamples: 0,
    validPoseSamples: 0,
    poseDetectionSamples: 0,
    analyzedDurationMs: 0,
    headCenteredSamples: 0,
    headUprightSamples: 0,
    shoulderUprightSamples: 0,
    bodyCenteredSamples: 0,
    stablePoseSamples: 0,
    facialDynamicSamples: 0,
    mouthDynamicSamples: 0,
    mouthSamples: 0,
    noFaceEvents: 0,
    headDeviationEvents: 0,
    headTiltEvents: 0,
    postureEvents: 0,
    movementEvents: 0,
    responseDelayMs: 0,
    responseDelayCount: 0,
    voiceQuestions: 0
  };

  for (const item of questionResults) {
    aggregate.faceDetectionSamples += item.faceDetectionSamples || 0;
    aggregate.validFaceSamples += item.validFaceSamples || 0;
    aggregate.poseDetectionSamples += item.poseDetectionSamples || 0;
    aggregate.validPoseSamples += item.validPoseSamples || 0;
    aggregate.sampleCount += (item.faceDetectionSamples || 0) + (item.poseDetectionSamples || 0);
    aggregate.analyzedDurationMs += item.durationMs || 0;
    aggregate.headCenteredSamples += item.headCenteredSamples || 0;
    aggregate.headUprightSamples += item.headUprightSamples || 0;
    aggregate.shoulderUprightSamples += item.shoulderUprightSamples || 0;
    aggregate.bodyCenteredSamples += item.bodyCenteredSamples || 0;
    aggregate.stablePoseSamples += item.stablePoseSamples || 0;
    aggregate.facialDynamicSamples += item.facialDynamicSamples || 0;
    aggregate.mouthDynamicSamples += item.mouthDynamicSamples || 0;
    aggregate.mouthSamples += item.mouthSamples || 0;
    aggregate.noFaceEvents += item.noFaceEvents || 0;
    aggregate.headDeviationEvents += item.headDeviationEvents || 0;
    aggregate.headTiltEvents += item.headTiltEvents || 0;
    aggregate.postureEvents += item.postureEvents || 0;
    aggregate.movementEvents += item.movementEvents || 0;
    if (Number.isFinite(item.responseDelayMs)) {
      aggregate.responseDelayMs += Math.max(0, item.responseDelayMs);
      aggregate.responseDelayCount += 1;
    }
    if (item.inputMode === 'voice') aggregate.voiceQuestions += 1;
  }
  return aggregate;
}

function responseDelayScore(milliseconds) {
  const seconds = milliseconds / 1000;
  if (seconds <= 3) return 100;
  if (seconds <= 8) return 92;
  if (seconds <= 15) return 84;
  if (seconds <= 30) return 74;
  return 65;
}

export function scoreNonverbal(questionResults, fallbackReason = null) {
  const items = Array.isArray(questionResults) ? questionResults : [];
  const total = aggregateQuestionResults(items);
  const statistics = {
    question_count: total.questionCount,
    sample_count: total.sampleCount,
    valid_face_samples: total.validFaceSamples,
    analyzed_duration_seconds: roundedSeconds(total.analyzedDurationMs),
    face_presence_ratio: Math.round(ratio(total.validFaceSamples, total.faceDetectionSamples) * 1000) / 1000,
    no_face_events: total.noFaceEvents,
    head_deviation_events: total.headDeviationEvents,
    posture_events: total.headTiltEvents + total.postureEvents,
    movement_events: total.movementEvents,
    average_response_delay_seconds: total.responseDelayCount
      ? roundedSeconds(total.responseDelayMs / total.responseDelayCount)
      : null
  };

  if (total.analyzedDurationMs < 8000) {
    return createInsufficientResult(fallbackReason || 'answer_too_short', statistics);
  }
  if (total.validFaceSamples < 20) {
    return createInsufficientResult(fallbackReason || 'insufficient_face_samples', statistics);
  }

  const facePresence = ratio(total.validFaceSamples, total.faceDetectionSamples);
  const headCentered = ratio(total.headCenteredSamples, total.validFaceSamples, 0.8);
  const headUpright = ratio(total.headUprightSamples, total.validFaceSamples, 0.8);
  const shoulderUpright = ratio(total.shoulderUprightSamples, total.validPoseSamples, 0.8);
  const bodyCentered = ratio(total.bodyCenteredSamples, total.validPoseSamples, 0.8);
  const stablePose = ratio(total.stablePoseSamples, total.validPoseSamples, 0.8);
  const facialActivity = ratio(total.facialDynamicSamples, total.validFaceSamples, 0.35);
  const mouthActivity = ratio(total.mouthDynamicSamples, total.mouthSamples, 0.35);
  const eventScale = Math.max(1, total.questionCount * 2);
  const awayContinuity = 1 - clamp(total.noFaceEvents / eventScale, 0, 1);
  const movementContinuity = 1 - clamp(total.movementEvents / eventScale, 0, 1);
  const averageDelay = total.responseDelayCount ? total.responseDelayMs / total.responseDelayCount : 5000;

  const cameraAttention = rounded(
    facePresence * 65 + headCentered * 35 - Math.min(15, total.noFaceEvents * 4)
  );
  const bodyPosture = rounded(
    headUpright * 45 + shoulderUpright * 35 + bodyCentered * 20
      - Math.min(16, (total.headTiltEvents + total.postureEvents) * 4)
  );
  const movementStability = rounded(stablePose * 70 + movementContinuity * 30);
  const interactionState = rounded(
    facePresence * 45 + responseDelayScore(averageDelay) * 0.35 + awayContinuity * 20
  );
  const baseFacialDynamics = clamp(80 + Math.min(12, facialActivity * 20) - (1 - facePresence) * 15);
  const facialDynamics = rounded(total.voiceQuestions
    ? baseFacialDynamics * 0.75 + clamp(72 + mouthActivity * 24) * 0.25
    : baseFacialDynamics);

  const dimensions = {
    camera_attention: cameraAttention,
    body_posture: bodyPosture,
    movement_stability: movementStability,
    interaction_state: interactionState,
    facial_dynamics: facialDynamics
  };
  const totalScore = rounded(
    cameraAttention * 0.25
      + bodyPosture * 0.20
      + movementStability * 0.20
      + interactionState * 0.20
      + facialDynamics * 0.15
  );

  const strengths = [];
  if (cameraAttention >= 80) strengths.push('大部分回答时间保持在摄像头画面内。');
  if (bodyPosture >= 80) strengths.push('回答期间头部和上半身姿态较稳定。');
  if (movementStability >= 80) strengths.push('回答期间动作幅度自然且稳定。');
  if (!strengths.length) strengths.push('已完成有效的非语言表现采样。');

  const suggestions = [];
  if (total.noFaceEvents) suggestions.push('部分回答曾持续离开画面，建议保持在摄像头取景范围内。');
  if (total.headDeviationEvents) suggestions.push('部分回答存在持续低头或转头，建议适当提高视线。');
  if (total.headTiltEvents || total.postureEvents) suggestions.push('可适当调整坐姿，使头部和肩膀保持自然平衡。');
  if (!suggestions.length) suggestions.push('继续保持自然交流，不必刻意控制表情或动作。');

  return {
    status: 'complete',
    reason: null,
    message: null,
    total_score: totalScore,
    dimensions,
    statistics,
    strengths: strengths.slice(0, 5),
    suggestions: suggestions.slice(0, 5)
  };
}
