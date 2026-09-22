'use client'
import {useEffect,useState} from 'react'
import {api} from './api'
import type {Project} from '@/types/aimpf'

export function useProjectId(){
  const [projectId,setProjectIdState]=useState('1')
  useEffect(()=>{const saved=localStorage.getItem('aimpf_project_id'); if(saved)setProjectIdState(saved)},[])
  function setProjectId(id:string){setProjectIdState(id);localStorage.setItem('aimpf_project_id',id)}
  return {projectId,setProjectId}
}

export function useProjects(){
  const [projects,setProjects]=useState<Project[]>([]); const [loading,setLoading]=useState(true)
  async function load(){setLoading(true);try{setProjects(await api<Project[]>('/api/projects'))}finally{setLoading(false)}}
  useEffect(()=>{load()},[])
  return {projects,loading,load}
}
