import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { register } from '../../api'

const Register = () => {
  const [username, setUsername] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const navigate = useNavigate()

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await register({ username, password })
      navigate('/login')
    } catch (error) {
      console.error('Registration failed', error)
    }
  }

  return (
    <form onSubmit={handleRegister}>
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
      <button type="submit">Register</button>
    </form>
  )
}

export default Register
