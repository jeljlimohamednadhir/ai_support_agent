import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import Layout from './components/Layout'
import LoadingScreen from './components/LoadingScreen'
import { LoginPage } from './pages/LoginPage'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import CollectionPage from './pages/CollectionPage'
import JiraPage from './pages/JiraPage'
import ValidationPage from './pages/ValidationPage'
import { ClassificationMLPage } from './pages/ClassificationMLPage'
import KnowledgePage from './pages/KnowledgePage'
import { ProfilePage } from './pages/ProfilePage'
import { UserManagementPage } from './pages/UserManagementPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  const [isReady, setIsReady] = useState(false)
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    // Vérifier immédiatement si le backend est prêt
    const checkBackend = async () => {
      try {
        const response = await fetch('/ready', {
          signal: AbortSignal.timeout(1000)
        })
        const data = await response.json()
        if (data.ready) {
          setIsReady(true)
        }
      } catch (err) {
        // Backend pas prêt, on va afficher l'écran de chargement
      } finally {
        setIsChecking(false)
      }
    }
    
    checkBackend()
  }, [])

  if (isChecking) {
    // Ne rien afficher pendant la vérification initiale rapide (1 seconde max)
    return null
  }

  if (!isReady) {
    return <LoadingScreen onReady={() => setIsReady(true)} />
  }

  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public route */}
          <Route path="/login" element={<LoginPage />} />
          
          {/* Protected routes */}
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="jira" element={<JiraPage />} />
            <Route path="classification-ml" element={<ClassificationMLPage />} />
            <Route path="knowledge" element={<KnowledgePage />} />
            <Route path="profile" element={<ProfilePage />} />
            
            {/* Admin only routes */}
            <Route path="collection" element={<ProtectedRoute requiredRole="ADMIN"><CollectionPage /></ProtectedRoute>} />
            <Route path="validation" element={<ProtectedRoute requiredRole="ADMIN"><ValidationPage /></ProtectedRoute>} />
            <Route path="settings" element={<ProtectedRoute requiredRole="ADMIN"><SettingsPage /></ProtectedRoute>} />
            <Route path="users" element={<ProtectedRoute requiredRole="ADMIN"><UserManagementPage /></ProtectedRoute>} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
