import { createRouter, createWebHistory } from 'vue-router';
import DashboardPage from '../pages/DashboardPage.vue';
import LoginPage from '../pages/LoginPage.vue';
import StudyPlanPage from '../pages/StudyPlanPage.vue';
import UploadPage from '../pages/UploadPage.vue';
import WrittenExamPage from '../pages/WrittenExamPage.vue';
import TextInterviewPage from '../pages/TextInterviewPage.vue';
import ReportPage from '../pages/ReportPage.vue';
import AvatarPage from '../pages/AvatarPage.vue';
import FavoritesPage from '../pages/FavoritesPage.vue';
import SettingsPage from '../pages/SettingsPage.vue';
import CareerAssessmentPage from '../pages/CareerAssessmentPage.vue';
import SimulationInterviewPage from '../pages/SimulationInterviewPage.vue';
import SceneIntroPage from '../pages/SceneIntroPage.vue';
import CompanyExamPage from '../pages/CompanyExamPage.vue';
import JobRecommendationsPage from '../pages/JobRecommendationsPage.vue';

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: LoginPage },
  { path: '/dashboard', name: 'dashboard', component: DashboardPage },
  { path: '/study-plan', name: 'study-plan', component: StudyPlanPage },
  { path: '/job-recommendations', name: 'job-recommendations', component: JobRecommendationsPage },
  { path: '/company-exams', name: 'company-exams', component: CompanyExamPage },
  { path: '/upload', name: 'upload', component: UploadPage },
  { path: '/exam', name: 'exam', component: WrittenExamPage },
  { path: '/interview', name: 'interview', component: TextInterviewPage },
  { path: '/report', name: 'report', component: ReportPage },
  { path: '/favorites', name: 'favorites', component: FavoritesPage },
  { path: '/avatar', name: 'avatar', component: AvatarPage },
  { path: '/simulation-interview', name: 'simulation-interview', component: SimulationInterviewPage },
  { path: '/scene/:sceneId', name: 'scene-intro', component: SceneIntroPage },
  { path: '/me', name: 'me', component: SettingsPage },
  { path: '/settings', redirect: '/me' },
  { path: '/career-assessment', name: 'career-assessment', component: CareerAssessmentPage },
  {
    path: '/career-assessment/:assessmentId',
    name: 'assessment-legacy',
    redirect: '/career-assessment'
  }
];

export default createRouter({ history: createWebHistory(), routes });
