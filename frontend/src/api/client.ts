import createClient from 'openapi-fetch'
import type { paths } from './schema'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export const api = createClient<paths>({
  baseUrl: API_BASE_URL,
  credentials: 'include', // Important: sends cookies with requests
})

// Add response interceptor to handle invalid/expired tokens
api.use({
  async onResponse({ response }) {
    // If we get a 401, the token is invalid/expired
    if (response.status === 401) {
      // Clear auth cookies by calling logout endpoint
      try {
        await fetch(`${API_BASE_URL}/api/auth/logout/`, {
          method: 'POST',
          credentials: 'include',
        })
      } catch {
        // Ignore errors during cleanup
      }

      // Redirect to login only if not already on an auth page
      if (typeof window !== 'undefined') {
        const pathname = window.location.pathname
        if (
          !pathname.startsWith('/login') &&
          !pathname.startsWith('/register') &&
          !pathname.startsWith('/forgot-password')
        ) {
          window.location.href = '/login'
        }
      }
    }
    return response
  },
})
