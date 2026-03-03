import { useState, useEffect } from 'react'
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { MessageSquare, LayoutDashboard, CheckSquare, BookOpen, Settings, Database, Activity, Brain, Menu, X, ChevronLeft, ChevronRight, Moon, Sun, Sparkles, User, LogOut, Shield, Users } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout, isAdmin } = useAuth()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    return saved ? JSON.parse(saved) : false
  })
  
  useEffect(() => {
    console.log('Dark mode state changed:', darkMode)
    if (darkMode) {
      document.documentElement.classList.add('dark')
      console.log('Added dark class to html element')
    } else {
      document.documentElement.classList.remove('dark')
      console.log('Removed dark class from html element')
    }
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
    console.log('HTML classList:', document.documentElement.classList.toString())
  }, [darkMode])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }
  
  // Define all navigation items
  const allNavItems = [
    { path: '/chat', icon: MessageSquare, label: 'Discussion', roles: ['USER', 'EXPERT', 'ADMIN'] },
    { path: '/dashboard', icon: LayoutDashboard, label: 'Tableau de bord', roles: ['USER', 'EXPERT', 'ADMIN'] },
    { path: '/jira', icon: Activity, label: 'Jira', roles: ['USER', 'EXPERT', 'ADMIN'] },
    { path: '/classification-ml', icon: Sparkles, label: 'Classification ML', roles: ['USER', 'EXPERT', 'ADMIN'] },
    { path: '/collection', icon: Database, label: 'Collection de données', roles: ['ADMIN'] },
    { path: '/validation', icon: CheckSquare, label: 'Validation', roles: ['EXPERT', 'ADMIN'] },
    { path: '/users', icon: Users, label: 'Utilisateurs', roles: ['ADMIN'] },
    { path: '/settings', icon: Settings, label: 'Paramètres', roles: ['USER', 'EXPERT', 'ADMIN'] },
  ]

  // Filter navigation items based on user role
  const navItems = allNavItems.filter(item => 
    user && item.roles.includes(user.role.toUpperCase())
  )
  
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-blue-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      {/* Sidebar */}
      <aside 
        className={`bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ease-in-out relative shadow-lg ${
          sidebarCollapsed ? 'w-20' : 'w-72'
        }`}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-100 dark:border-gray-700">
          {!sidebarCollapsed ? (
            <>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-blue-600 bg-clip-text text-transparent">
                Agent IA Support
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {user?.full_name || user?.username}
              </p>
            </>
          ) : (
            <div className="flex justify-center">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
                {user?.username?.charAt(0).toUpperCase()}
              </div>
            </div>
          )}
        </div>
        
        {/* Navigation */}
        <nav className="mt-4 px-3">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 mb-1 text-sm font-medium rounded-lg transition-all duration-200 ${
                  isActive
                    ? 'text-white bg-gradient-to-r from-primary-600 to-blue-600 shadow-md'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-primary-600 dark:hover:text-primary-400'
                }`}
                title={sidebarCollapsed ? item.label : ''}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span className="ml-3">{item.label}</span>}
              </Link>
            )
          })}
        </nav>
        
        {/* Dark Mode Toggle & Profile Menu - Bottom */}
        <div className="absolute bottom-4 left-0 right-0 px-3 space-y-2">
          {/* Profile Menu */}
          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className={`flex items-center w-full px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                location.pathname === '/profile'
                  ? 'bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
              title={sidebarCollapsed ? 'Profil' : ''}
            >
              <User className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && (
                <>
                  <span className="ml-3 flex-1 text-left truncate">{user?.username}</span>
                  <Shield className="w-4 h-4 flex-shrink-0 opacity-50" />
                </>
              )}
            </button>

            {/* Profile Dropdown */}
            {showProfileMenu && !sidebarCollapsed && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-2">
                <Link
                  to="/profile"
                  onClick={() => setShowProfileMenu(false)}
                  className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <User className="w-4 h-4 mr-3" />
                  Mon profil
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <LogOut className="w-4 h-4 mr-3" />
                  Déconnexion
                </button>
              </div>
            )}
          </div>

          {/* Dark Mode Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`flex items-center w-full px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
              darkMode
                ? 'bg-gray-700 text-yellow-400 hover:bg-gray-600'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
            title={darkMode ? 'Mode clair' : 'Mode sombre'}
          >
            {darkMode ? <Sun className="w-5 h-5 flex-shrink-0" /> : <Moon className="w-5 h-5 flex-shrink-0" />}
            {!sidebarCollapsed && (
              <span className="ml-3">{darkMode ? 'Mode clair' : 'Mode sombre'}</span>
            )}
          </button>
        </div>
        
        {/* Collapse Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-24 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full p-1.5 shadow-md hover:shadow-lg transition-all duration-200 hover:scale-110"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-300" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-300" />
          )}
        </button>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
