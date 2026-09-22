export function token(){if(typeof window==='undefined') return ''; return localStorage.getItem('aimpf_token')||''}
export function setToken(v:string){localStorage.setItem('aimpf_token',v)}
export function clearToken(){localStorage.removeItem('aimpf_token')}
