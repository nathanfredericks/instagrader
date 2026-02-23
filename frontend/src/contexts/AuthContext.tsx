'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { getCurrentUser, refreshToken } from '@/lib/auth'
import type { components } from '@/api/schema'

type User = components['schemas']['User']

interface AuthContextType {
  user: User | null
  loading: boolean
  refreshAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshAuth = async () => {
    const currentUser = await getCurrentUser()

    // If getCurrentUser returns null, it means:
    // 1. Token is invalid/expired
    // 2. User doesn't exist
    // 3. Not authenticated
    // The API client interceptor will handle the redirect to /login
    setUser(currentUser)
    setLoading(false)
  }

  useEffect(() => {
    refreshAuth()

    // Set up token refresh interval (every 50 minutes for 60-minute tokens)
    const interval = setInterval(async () => {
      const success = await refreshToken()
      if (success) {
        await refreshAuth()
      } else {
        // If refresh fails, the user is no longer authenticated
        // The API client interceptor will handle redirect to /login
        setUser(null)
      }
    }, 50 * 60 * 1000)

    return () => clearInterval(interval)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
