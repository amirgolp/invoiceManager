import { useTheme } from '../theme'

const ThemeToggle = () => {
  const { darkMode, toggleTheme } = useTheme()

  return (
    <button onClick={toggleTheme}>
      {darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
    </button>
  )
}

export default ThemeToggle
