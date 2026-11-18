import { Routes } from '@angular/router';
import { CommunitiesHome } from './communities-home';
import { CommunityPage } from './community-page';
import { PostPage } from './post-page';

export const routes: Routes = [
  { path: '', component: CommunitiesHome },
  { path: 'post/:id', component: PostPage },
  { path: ':id', component: CommunityPage },
];
