'use client'
import {useProjectId,useProjects} from '@/lib/project'
export default function ProjectSelect(){
 const {projects}=useProjects(); const {projectId,setProjectId}=useProjectId()
 return <select aria-label="Project" className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm" value={projectId} onChange={e=>{setProjectId(e.target.value);location.reload()}}>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select>
}
