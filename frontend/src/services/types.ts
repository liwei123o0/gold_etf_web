export interface User {
  id: number
  username: string
  created_at?: string
}

export interface AuthResponse {
  success: boolean
  user?: User
  error?: string
  token?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}
