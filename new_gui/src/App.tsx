import { BrowserRouter as Router, Route, Routes } from 'react-router-dom'
import Navbar from './components/Layout/Navbar'
import Sidebar from './components/Layout/Sidebar'
import HomePage from './pages/HomePage'
import UserPage from './pages/UserPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ChatPage from './pages/ChatPage'
import { ThemeProvider } from './theme'

const App = () => (
  <ThemeProvider>
    <Router>
      <Navbar />
      <Sidebar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/profile" element={<UserPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Router>
  </ThemeProvider>
)

export default App