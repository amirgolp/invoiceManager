import { useEffect, useState } from 'react'
import { getUserProfile } from '../api'

interface UserProfile {
  username: string
  email: string
}

const UserProfile = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null)

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const userProfile = await getUserProfile()
        setProfile(userProfile)
      } catch (error) {
        console.error('Failed to load profile', error)
      }
    }

    fetchProfile()
  }, [])

  return (
    <div>
      {profile ? (
        <div>
          <h1>Welcome, {profile.username}</h1>
          <p>Email: {profile.email}</p>
        </div>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  )
}

export default UserProfile
