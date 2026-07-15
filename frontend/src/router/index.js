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

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', name: 'login', component: LoginPage },
  { path: '/dashboard', name: 'dashboard', component: DashboardPage },
  { path: '/study-plan', name: 'study-plan', component: StudyPlanPage },
  { path: '/upload', name: 'upload', component: UploadPage },
  { path: '/exam', name: 'exam', component: WrittenExamPage },
  { path: '/interview', name: 'interview', component: TextInterviewPage },
  { path: '/report', name: 'report', component: ReportPage },
  { path: '/favorites', name: 'favorites', component: FavoritesPage },
  { path: '/avatar', name: 'avatar', component: AvatarPage },
  { path: '/settings', name: 'settings', component: SettingsPage },
  { path: '/career-assessment', name: 'career-assessment', component: CareerAssessmentPage },
  {
    path: '/career-assessment/:assessmentId',
    name: 'assessment-legacy',
    redirect: '/career-assessment'
  }
];

export default createRouter({ history: createWebHistory(), routes });
