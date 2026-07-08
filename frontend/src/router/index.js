import { createRouter, createWebHistory } from 'vue-router';
import DashboardPage from '../pages/DashboardPage.vue';
import LoginPage from '../pages/LoginPage.vue';
import UploadPage from '../pages/UploadPage.vue';
import WrittenExamPage from '../pages/WrittenExamPage.vue';
import TextInterviewPage from '../pages/TextInterviewPage.vue';
import ReportPage from '../pages/ReportPage.vue';
import AvatarPage from '../pages/AvatarPage.vue';

const routes = [
  { path: '/', name: 'dashboard', component: DashboardPage },
  { path: '/login', name: 'login', component: LoginPage },
  { path: '/upload', name: 'upload', component: UploadPage },
  { path: '/exam', name: 'exam', component: WrittenExamPage },
  { path: '/interview', name: 'interview', component: TextInterviewPage },
  { path: '/report', name: 'report', component: ReportPage },
  { path: '/avatar', name: 'avatar', component: AvatarPage }
];

export default createRouter({
  history: createWebHistory(),
  routes
});
