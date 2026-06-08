import { describe, expect, it } from 'vitest'
import {
  loginResponseSchema,
  loginSchema,
  newPasswordSchema,
  refreshResponseSchema,
} from './schemas'

describe('auth schemas', () => {
  it('validates login form inputs', () => {
    expect(loginSchema.parse({ username: 'user@example.com', password: 'secret' })).toEqual({
      username: 'user@example.com',
      password: 'secret',
    })
    expect(() => loginSchema.parse({ username: 'bad-email', password: 'secret' })).toThrow()
  })

  it('validates first-login password rules', () => {
    expect(() =>
      newPasswordSchema.parse({ newPassword: 'Password1', confirmPassword: 'Password1' }),
    ).not.toThrow()
    expect(() =>
      newPasswordSchema.parse({ newPassword: 'password', confirmPassword: 'password' }),
    ).toThrow()
  })

  it('accepts token and challenge auth responses', () => {
    expect(() =>
      loginResponseSchema.parse({
        id_token: 'id',
        access_token: 'access',
        refresh_token: 'refresh',
      }),
    ).not.toThrow()

    expect(() =>
      loginResponseSchema.parse({
        challenge_name: 'NEW_PASSWORD_REQUIRED',
        session: 'session',
        parameters: {},
      }),
    ).not.toThrow()

    expect(refreshResponseSchema.parse({ id_token: 'id', access_token: 'access' })).toEqual({
      id_token: 'id',
      access_token: 'access',
    })
  })
})
