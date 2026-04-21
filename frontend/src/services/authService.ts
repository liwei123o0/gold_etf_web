import api from './api'

export interface User {
  id: number
  username: string
  created_at?: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface AuthResponse {
  success: boolean
  user?: User
  error?: string
  token?: string
}

export const authService = {
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', data)
    return response.data
  },

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/register', data)
    return response.data
  },

  async logout(): Promise<void> {
    await api.post('/auth/logout')
  },

  async getMe(): Promise<AuthResponse> {
    const response = await api.get<AuthResponse>('/auth/me')
    return response.data
  }
}
