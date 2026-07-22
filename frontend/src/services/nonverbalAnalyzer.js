import { scoreNonverbal } from './nonverbalScorer.js';

export const MEDIAPIPE_CONFIG = Object.freeze({
  packageVersion: '0.10.35',
  wasmRoot: 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm',
  faceModelUrl: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
  poseModelUrl: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
  faceIntervalMs: 300,
  poseIntervalMs: 600,
  analysisWidth: 480,
  analysisHeight: 270
});

const EVENT_THRESHOLDS = Object.freeze({
  noFace: 2000,
  headDeviation: 3000,
  headTilt: 3000,
  posture: 4000,
  movement: 1500
});

function average(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function distance(left, right) {
  return Math.hypot((left?.x || 0) - (right?.x || 0), (left?.y || 0) - (right?.y || 0));
}

function midpoint(left, right) {
  return { x: ((left?.x || 0) + (right?.x || 0)) / 2, y: ((left?.y || 0) + (right?.y || 0)) / 2 };
}

function radiansToDegrees(value) {
  return value * 180 / Math.PI;
}

function matrixToEuler(matrix) {
  const data = matrix?.data;
  if (!data || data.length < 16) return null;
  const m00 = data[0];
  const m10 = data[1];
  const m11 = data[5];
  const m12 = data[9];
  const m02 = data[8];
  const m22 = data[10];
  return {
    yaw: radiansToDegrees(Math.atan2(m02, m22)),
    pitch: radiansToDegrees(Math.atan2(-m12, Math.hypot(m10, m11))),
    roll: radiansToDegrees(Math.atan2(m10, m11 || m00))
  };
}

function updateContinuousEvent(question, key, active, timestamp, threshold, counter) {
  const streak = question._streaks[key];
  if (!active) {
    streak.startedAt = null;
    streak.recorded = false;
    return;
  }
  if (streak.startedAt === null) streak.startedAt = timestamp;
  if (!streak.recorded && timestamp - streak.startedAt >= threshold) {
    question[counter] += 1;
    streak.recorded = true;
  }
}

export function createQuestionMetrics(questionId, context = {}) {
  return {
    questionId,
    inputMode: context.inputMode || 'text',
    presentedAt: Number.isFinite(context.presentedAt) ? context.presentedAt : null,
    answerStartedAt: Number.isFinite(context.answerStartedAt) ? context.answerStartedAt : Date.now(),
    submittedAt: null,
    responseDelayMs: null,
    durationMs: 0,
    faceDetectionSamples: 0,
    validFaceSamples: 0,
    poseDetectionSamples: 0,
    validPoseSamples: 0,
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
    _activeStartedAt: null,
    _faceBaseline: { yaw: [], pitch: [], roll: [], centerX: [], centerY: [], faceSize: [] },
    _poseBaseline: { shoulderCenterX: [], shoulderCenterY: [], bodyCenterX: [], bodyCenterY: [], shoulderWidth: [], shoulderTilt: [] },
    _previousFace: null,
    _previousBodyCenter: null,
    _streaks: Object.fromEntries(
      ['noFace', 'headDeviation', 'headTilt', 'posture', 'movement']
        .map((key) => [key, { startedAt: null, recorded: false }])
    )
  };
}

export function recordFaceObservation(question, observation, timestamp = Date.now()) {
  question.faceDetectionSamples += 1;
  const detected = Boolean(observation?.detected);
  updateContinuousEvent(question, 'noFace', !detected, timestamp, EVENT_THRESHOLDS.noFace, 'noFaceEvents');
  if (!detected) return;

  question.validFaceSamples += 1;
  const headDeviation = Boolean(observation.headDeviation);
  const headTilt = Boolean(observation.headTilt);
  if (!headDeviation) question.headCenteredSamples += 1;
  if (!headTilt) question.headUprightSamples += 1;
  if (observation.facialDynamic) question.facialDynamicSamples += 1;
  if (observation.mouthMeasured) {
    question.mouthSamples += 1;
    if (observation.mouthDynamic) question.mouthDynamicSamples += 1;
  }
  updateContinuousEvent(question, 'headDeviation', headDeviation, timestamp, EVENT_THRESHOLDS.headDeviation, 'headDeviationEvents');
  updateContinuousEvent(question, 'headTilt', headTilt, timestamp, EVENT_THRESHOLDS.headTilt, 'headTiltEvents');
}

export function recordPoseObservation(question, observation, timestamp = Date.now()) {
  question.poseDetectionSamples += 1;
  if (!observation?.detected) return;
  question.validPoseSamples += 1;
  const postureIssue = Boolean(observation.shoulderTilt || observation.bodyOffset);
  if (!observation.shoulderTilt) question.shoulderUprightSamples += 1;
  if (!observation.bodyOffset) question.bodyCenteredSamples += 1;
  if (!observation.excessiveMovement) question.stablePoseSamples += 1;
  updateContinuousEvent(question, 'posture', postureIssue, timestamp, EVENT_THRESHOLDS.posture, 'postureEvents');
  updateContinuousEvent(question, 'movement', Boolean(observation.excessiveMovement), timestamp, EVENT_THRESHOLDS.movement, 'movementEvents');
}

function extractFaceObservation(result, question) {
  const landmarks = result?.faceLandmarks?.[0];
  if (!landmarks?.length) return { detected: false };
  const rotation = matrixToEuler(result?.facialTransformationMatrixes?.[0]);
  if (!rotation) return { detected: false };

  const leftEye = landmarks[33];
  const rightEye = landmarks[263];
  const nose = landmarks[1];
  const upperLip = landmarks[13];
  const lowerLip = landmarks[14];
  const upperLeftEyelid = landmarks[159];
  const lowerLeftEyelid = landmarks[145];
  const faceSize = Math.max(distance(leftEye, rightEye), 0.0001);
  const mouthOpen = distance(upperLip, lowerLip) / faceSize;
  const eyeOpen = distance(upperLeftEyelid, lowerLeftEyelid) / faceSize;
  const centerX = nose?.x || midpoint(leftEye, rightEye).x;
  const centerY = nose?.y || midpoint(leftEye, rightEye).y;
  const baseline = question._faceBaseline;

  if (baseline.yaw.length < 8) {
    baseline.yaw.push(rotation.yaw);
    baseline.pitch.push(rotation.pitch);
    baseline.roll.push(rotation.roll);
    baseline.centerX.push(centerX);
    baseline.centerY.push(centerY);
    baseline.faceSize.push(faceSize);
  }

  const yawDelta = Math.abs(rotation.yaw - average(baseline.yaw));
  const pitchDelta = Math.abs(rotation.pitch - average(baseline.pitch));
  const rollDelta = Math.abs(rotation.roll - average(baseline.roll));
  const centerDelta = Math.hypot(
    centerX - average(baseline.centerX),
    centerY - average(baseline.centerY)
  ) / Math.max(average(baseline.faceSize), 0.0001);
  const previous = question._previousFace;
  const mouthDynamic = Boolean(previous && Math.abs(mouthOpen - previous.mouthOpen) > 0.012);
  const facialDynamic = Boolean(previous && (
    mouthDynamic
      || Math.abs(eyeOpen - previous.eyeOpen) > 0.006
      || Math.hypot(centerX - previous.centerX, centerY - previous.centerY) / faceSize > 0.015
  ));
  question._previousFace = { mouthOpen, eyeOpen, centerX, centerY };

  return {
    detected: true,
    headDeviation: baseline.yaw.length >= 8 && (yawDelta > 15 || pitchDelta > 12 || centerDelta > 0.45),
    headTilt: baseline.roll.length >= 8 && rollDelta > 12,
    facialDynamic,
    mouthMeasured: true,
    mouthDynamic
  };
}

function visibleLandmark(landmark) {
  return landmark && (landmark.visibility === undefined || landmark.visibility >= 0.45);
}

function extractPoseObservation(result, question) {
  const landmarks = result?.landmarks?.[0];
  if (!landmarks?.length) return { detected: false };
  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];
  const leftHip = landmarks[23];
  const rightHip = landmarks[24];
  if (![leftShoulder, rightShoulder, leftHip, rightHip].every(visibleLandmark)) {
    return { detected: false };
  }

  const shoulderCenter = midpoint(leftShoulder, rightShoulder);
  const hipCenter = midpoint(leftHip, rightHip);
  const bodyCenter = midpoint(shoulderCenter, hipCenter);
  const shoulderWidth = Math.max(distance(leftShoulder, rightShoulder), 0.0001);
  const shoulderTilt = radiansToDegrees(Math.atan2(
    rightShoulder.y - leftShoulder.y,
    rightShoulder.x - leftShoulder.x
  ));
  const baseline = question._poseBaseline;
  if (baseline.shoulderCenterX.length < 4) {
    baseline.shoulderCenterX.push(shoulderCenter.x);
    baseline.shoulderCenterY.push(shoulderCenter.y);
    baseline.bodyCenterX.push(bodyCenter.x);
    baseline.bodyCenterY.push(bodyCenter.y);
    baseline.shoulderWidth.push(shoulderWidth);
    baseline.shoulderTilt.push(shoulderTilt);
  }

  const baseWidth = Math.max(average(baseline.shoulderWidth), 0.0001);
  const baseBody = { x: average(baseline.bodyCenterX), y: average(baseline.bodyCenterY) };
  const bodyOffset = distance(bodyCenter, baseBody) / baseWidth > 0.35;
  const excessiveMovement = Boolean(
    question._previousBodyCenter
      && distance(bodyCenter, question._previousBodyCenter) / baseWidth > 0.12
  );
  question._previousBodyCenter = bodyCenter;
  return {
    detected: true,
    shoulderTilt: baseline.shoulderTilt.length >= 4
      && Math.abs(shoulderTilt - average(baseline.shoulderTilt)) > 10,
    bodyOffset: baseline.bodyCenterX.length >= 4 && bodyOffset,
    excessiveMovement
  };
}

export function createNonverbalAnalyzer({ onStateChange = null, detectorFactory = null } = {}) {
  let state = 'idle';
  let failureReason = null;
  let loadAttempted = false;
  let initializePromise = null;
  let videoElement = null;
  let faceLandmarker = null;
  let poseLandmarker = null;
  let analysisCanvas = null;
  let analysisContext = null;
  let timer = null;
  let shouldAnalyze = false;
  let activeQuestion = null;
  let faceInterval = MEDIAPIPE_CONFIG.faceIntervalMs;
  let poseInterval = MEDIAPIPE_CONFIG.poseIntervalMs;
  let slowFaceRuns = 0;
  let nextFaceAt = 0;
  let nextPoseAt = 0;
  const completedQuestions = [];
  const completedById = new Map();

  function setState(nextState) {
    state = nextState;
    onStateChange?.(state);
  }

  function stopTimer() {
    if (timer !== null) window.clearTimeout(timer);
    timer = null;
  }

  function suspendClock(now = Date.now()) {
    if (activeQuestion && activeQuestion._activeStartedAt !== null) {
      activeQuestion.durationMs += Math.max(0, now - activeQuestion._activeStartedAt);
      activeQuestion._activeStartedAt = null;
    }
  }

  function resumeClock(now = Date.now()) {
    if (activeQuestion && activeQuestion._activeStartedAt === null) {
      activeQuestion._activeStartedAt = now;
    }
  }

  function canDetect() {
    return state === 'available'
      && shouldAnalyze
      && activeQuestion
      && document.visibilityState === 'visible'
      && videoElement?.readyState >= 2
      && videoElement.videoWidth > 0;
  }

  function handleAnalysisError(error) {
    console.warn('非语言分析已降级：', error);
    failureReason = 'analysis_error';
    shouldAnalyze = false;
    suspendClock();
    stopTimer();
    setState('unavailable');
  }

  function scheduleNextDetection() {
    stopTimer();
    if (!canDetect()) return;
    const now = performance.now();
    const nextDue = Math.min(nextFaceAt, nextPoseAt);
    timer = window.setTimeout(runDetection, Math.max(0, nextDue - now));
  }

  function runDetection() {
    timer = null;
    if (!canDetect()) return;
    const startedAt = performance.now();
    try {
      analysisContext.drawImage(
        videoElement,
        0,
        0,
        MEDIAPIPE_CONFIG.analysisWidth,
        MEDIAPIPE_CONFIG.analysisHeight
      );
      const faceDue = startedAt >= nextFaceAt;
      const poseDue = startedAt >= nextPoseAt;
      if (faceDue && (!poseDue || nextFaceAt <= nextPoseAt)) {
        const result = faceLandmarker.detectForVideo(analysisCanvas, startedAt);
        recordFaceObservation(activeQuestion, extractFaceObservation(result, activeQuestion));
        nextFaceAt = startedAt + faceInterval;
        const cost = performance.now() - startedAt;
        slowFaceRuns = cost > 180 ? slowFaceRuns + 1 : 0;
        if (slowFaceRuns >= 3) faceInterval = 500;
      } else {
        const result = poseLandmarker.detectForVideo(analysisCanvas, startedAt);
        recordPoseObservation(activeQuestion, extractPoseObservation(result, activeQuestion));
        nextPoseAt = startedAt + poseInterval;
        if (performance.now() - startedAt > 200) poseInterval = 900;
      }
    } catch (error) {
      handleAnalysisError(error);
      return;
    }
    scheduleNextDetection();
  }

  function handleVisibilityChange() {
    if (document.visibilityState !== 'visible') {
      stopTimer();
      suspendClock();
      return;
    }
    if (shouldAnalyze && activeQuestion) {
      resumeClock();
      const now = performance.now();
      nextFaceAt = now;
      nextPoseAt = now + 150;
      scheduleNextDetection();
    }
  }

  async function initialize(element) {
    if (state === 'destroyed') return state;
    if (state === 'available') {
      videoElement = element;
      return state;
    }
    if (initializePromise) return initializePromise;
    if (loadAttempted) return state;
    loadAttempted = true;
    videoElement = element;
    setState('initializing');
    initializePromise = (async () => {
      try {
        if (detectorFactory) {
          ({ faceLandmarker, poseLandmarker } = await detectorFactory());
        } else {
          const { FaceLandmarker, FilesetResolver, PoseLandmarker } = await import('@mediapipe/tasks-vision');
          const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_CONFIG.wasmRoot);
          faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: MEDIAPIPE_CONFIG.faceModelUrl },
            runningMode: 'VIDEO',
            numFaces: 1,
            outputFacialTransformationMatrixes: true,
            outputFaceBlendshapes: false
          });
          poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: MEDIAPIPE_CONFIG.poseModelUrl },
            runningMode: 'VIDEO',
            numPoses: 1
          });
        }
        analysisCanvas = document.createElement('canvas');
        analysisCanvas.width = MEDIAPIPE_CONFIG.analysisWidth;
        analysisCanvas.height = MEDIAPIPE_CONFIG.analysisHeight;
        analysisContext = analysisCanvas.getContext('2d', { alpha: false });
        if (!analysisContext) throw new Error('浏览器无法创建分析画布');
        document.addEventListener('visibilitychange', handleVisibilityChange);
        setState('available');
      } catch (error) {
        console.warn('MediaPipe 初始化失败，面试将继续：', error);
        failureReason = 'model_load_failed';
        setState('unavailable');
      }
      return state;
    })();
    return initializePromise;
  }

  function startQuestion(questionId, context = {}) {
    if (state !== 'available' || !questionId) return false;
    if (activeQuestion?.questionId === questionId) {
      if (context.inputMode === 'voice') activeQuestion.inputMode = 'voice';
      shouldAnalyze = true;
      resumeClock();
      const now = performance.now();
      nextFaceAt = now;
      nextPoseAt = now + 150;
      scheduleNextDetection();
      return true;
    }
    if (activeQuestion || completedById.has(questionId)) return false;
    activeQuestion = createQuestionMetrics(questionId, context);
    shouldAnalyze = true;
    resumeClock();
    const now = performance.now();
    nextFaceAt = now;
    nextPoseAt = now + 150;
    scheduleNextDetection();
    return true;
  }

  function markVoiceInput() {
    if (activeQuestion) activeQuestion.inputMode = 'voice';
  }

  function pause() {
    shouldAnalyze = false;
    stopTimer();
    suspendClock();
  }

  function finishQuestion(context = {}) {
    const questionId = context.questionId || activeQuestion?.questionId;
    if (!questionId) return null;
    if (completedById.has(questionId)) return completedById.get(questionId);
    if (!activeQuestion || activeQuestion.questionId !== questionId) return null;
    pause();
    activeQuestion.submittedAt = context.submittedAt || Date.now();
    activeQuestion.responseDelayMs = activeQuestion.presentedAt === null
      ? null
      : Math.max(0, activeQuestion.answerStartedAt - activeQuestion.presentedAt);
    const completed = { ...activeQuestion };
    for (const key of Object.keys(completed)) {
      if (key.startsWith('_')) delete completed[key];
    }
    completedQuestions.push(completed);
    completedById.set(questionId, completed);
    activeQuestion = null;
    return completed;
  }

  function generateFinalResult(options = {}) {
    const fallbackReason = failureReason || options.fallbackReason || null;
    return scoreNonverbal(completedQuestions, fallbackReason);
  }

  function destroy() {
    if (state === 'destroyed') return;
    pause();
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    faceLandmarker?.close();
    poseLandmarker?.close();
    faceLandmarker = null;
    poseLandmarker = null;
    analysisContext = null;
    analysisCanvas = null;
    videoElement = null;
    activeQuestion = null;
    setState('destroyed');
  }

  return {
    initialize,
    startQuestion,
    markVoiceInput,
    pause,
    finishQuestion,
    generateFinalResult,
    destroy,
    getState: () => state
  };
}
