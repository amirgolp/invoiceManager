import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../../api'

const Login = () => {
  const [username, setUsername] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const navigate = useNavigate()

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await login({ username, password })
      navigate('/profile')
    } catch (error) {
      console.error('Login failed', error)
    }
  }

  return (
    <form onSubmit={handleLogin}>
      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={e => setUsername(e.target.value)}
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
      />
      <button type="submit">Login</button>
    </form>
  )
}

export default Login
