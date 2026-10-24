// Login state lives in localStorage (set by AuthForm after a successful login).
export function getAuth() {
  return {
    token: localStorage.getItem('spd_token'),
    role: localStorage.getItem('spd_role'),
    name: localStorage.getItem('spd_name'),
  }
}

export function saveAuth({ token, role, name }) {
  localStorage.setItem('spd_token', token)
  localStorage.setItem('spd_role', role)
  localStorage.setItem('spd_name', name)
}

export function clearAuth() {
  localStorage.removeItem('spd_token')
  localStorage.removeItem('spd_role')
  localStorage.removeItem('spd_name')
}
