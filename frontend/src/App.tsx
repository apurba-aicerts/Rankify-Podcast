import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { NewPodcastPage } from './pages/NewPodcastPage'
import { ProjectPage } from './pages/ProjectPage'
import { ScriptReviewPage } from './pages/ScriptReviewPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/new" element={<NewPodcastPage />} />
        <Route path="/projects/:projectId/scripts/:scriptId" element={<ScriptReviewPage />} />
      </Routes>
    </BrowserRouter>
  )
}
