import axios from 'axios'

interface AuthCredentials {
  username: string
  password: string
}

const API_URL = 'http://localhost:8000' // Your FastAPI backend URL

export const login = async (credentials: AuthCredentials) => {
  try {
    const response = await axios.post(`${API_URL}/auth/login`, credentials, {
      headers: { 'Content-Type': 'application/json' }
    })
    localStorage.setItem('token', response.data.access_token)
  } catch (error) {
    throw new Error('Login failed')
  }
}

export const register = async (credentials: AuthCredentials) => {
  try {
    await axios.post(`${API_URL}/auth/register`, credentials, {
      headers: { 'Content-Type': 'application/json' }
    })
  } catch (error) {
    throw new Error('Registration failed')
  }
}

export const getUserProfile = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`${API_URL}/user/profile`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.data
  } catch (error) {
    throw new Error('Failed to fetch user profile')
  }
}
