import {token,clearToken} from './auth'
const API=process.env.NEXT_PUBLIC_API_URL||'http://127.0.0.1:8000'
export async function api<T>(path:string,init?:RequestInit):Promise<T>{
 const headers:HeadersInit={'Content-Type':'application/json',...(init?.headers||{})}; const t=token(); if(t) (headers as Record<string,string>).Authorization=`Bearer ${t}`
 const r=await fetch(`${API}${path}`,{...init,headers,cache:'no-store'}); if(r.status===401){clearToken()} if(!r.ok) throw new Error(await r.text()); return r.json() as Promise<T>
}
export function reportUrl(pid:string){return `${API}/api/projects/${pid}/report.pdf`}
