import { api } from '@/api/client'

/**
 * Get the current authenticated user.
 * Returns null if not authenticated or if token is invalid.
 */
export async function getCurrentUser() {
  try {
    const { data, error } = await api.GET('/api/auth/me/')

    // If 401 or user doesn't exist, the interceptor will handle redirect
    if (error || !data) return null

    return data
  } catch {
    return null
  }
}

/**
 * Logout the user by clearing auth cookies and redirecting to login.
 */
export async function logout() {
  try {
    await api.POST('/api/auth/logout/')
  } catch {
    // Ignore errors on logout
  }
  // Redirect to login
  window.location.href = '/login'
}

/**
 * Refresh the access token using the refresh token cookie.
 * Returns true if successful, false otherwise.
 */
export async function refreshToken() {
  try {
    const { error } = await api.POST('/api/auth/refresh/')

    // If refresh fails (401), the interceptor will handle redirect
    if (error) return false

    return true
  } catch {
    return false
  }
}
