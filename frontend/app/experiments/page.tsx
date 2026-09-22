'use client'
import {useEffect,useState} from 'react'
import {api} from '@/lib/api'
import {Card} from '@/components/ui/card'
import {useProjectId} from '@/lib/project'

export default function Experiments(){
  const {projectId}=useProjectId()
  const [rows,setRows]=useState<any[]>([])
  const [name,setName]=useState('Adaptive validation baseline comparison')
  const [hyp,setHyp]=useState('AIMPF should achieve useful uncertainty reduction at lower validation cost than simple deterministic baselines.')
  const [run,setRun]=useState<any>()
  const [busy,setBusy]=useState(false)
  const load=async()=>setRows(await api<any[]>(`/api/projects/${projectId}/experiments`))
  useEffect(()=>{load()},[projectId])
  async function create(){await api(`/api/projects/${projectId}/experiments`,{method:'POST',body:JSON.stringify({name,hypothesis:hyp})});await load()}
  async function execute(){
    setBusy(true)
    try{setRun(await api<any>(`/api/projects/${projectId}/experiments/run`,{method:'POST'}));await load()}
    catch(e:any){setRun({error:e.message})}
    finally{setBusy(false)}
  }
  return <main className="mx-auto max-w-7xl px-6 py-10">
    <p className="text-sm text-cyan-300">Research evidence</p>
    <h1 className="mt-2 text-4xl font-semibold">Experiments</h1>
    <p className="mt-3 max-w-3xl text-slate-400">Compare the adaptive selector with fixed deterministic baselines and a finite-set exact minimum-cost oracle. The evaluator is reproducible and does not claim statistical significance.</p>
    <div className="mt-7 grid gap-5 lg:grid-cols-2">
      <Card>
        <h2 className="font-semibold">Register experiment</h2>
        <input className="mt-4 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={name} onChange={e=>setName(e.target.value)}/>
        <textarea className="mt-3 min-h-24 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2" value={hyp} onChange={e=>setHyp(e.target.value)}/>
        <button onClick={create} className="mt-3 rounded-xl bg-cyan-400 px-4 py-2 font-semibold text-slate-950">Save experiment</button>
      </Card>
      <Card>
        <h2 className="font-semibold">Run baseline comparison</h2>
        <p className="mt-3 text-sm text-slate-400">AIMPF adaptive vs uncertainty-only, cheapest-first, full-suite, and exact minimum-cost oracle.</p>
        <button onClick={execute} disabled={busy} className="mt-5 rounded-xl bg-cyan-400 px-4 py-2 font-semibold text-slate-950 disabled:opacity-40">{busy?'Running…':'Run comparison'}</button>
        {run&&!run.error&&<div className="mt-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-slate-800 p-3"><div className="text-xs text-slate-500">AIMPF cost</div><div className="mt-1 text-xl">{run.adaptive_cost.toFixed(2)}</div></div>
            <div className="rounded-xl border border-slate-800 p-3"><div className="text-xs text-slate-500">Full suite</div><div className="mt-1 text-xl">{run.full_suite_cost.toFixed(2)}</div></div>
            <div className="rounded-xl border border-slate-800 p-3"><div className="text-xs text-slate-500">Cost reduction</div><div className="mt-1 text-xl">{(run.cost_reduction*100).toFixed(1)}%</div></div>
            <div className="rounded-xl border border-slate-800 p-3"><div className="text-xs text-slate-500">Uncertainty reduction</div><div className="mt-1 text-xl">{(run.uncertainty_reduction*100).toFixed(1)}%</div></div>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-sm"><thead className="border-b border-slate-800 text-slate-500"><tr><th className="px-3 py-2">Strategy</th><th className="px-3 py-2">Cost</th><th className="px-3 py-2">Reduction</th><th className="px-3 py-2">Uncertainty</th></tr></thead><tbody>{run.baseline_comparison?.strategies?.map((r:any)=><tr key={r.strategy} className="border-b border-slate-900"><td className="px-3 py-2">{r.strategy}</td><td className="px-3 py-2">{r.cost.toFixed(2)}</td><td className="px-3 py-2">{(r.cost_reduction*100).toFixed(1)}%</td><td className="px-3 py-2">{(r.uncertainty_reduction*100).toFixed(1)}%</td></tr>)}</tbody></table>
          </div>
          <p className="text-xs text-slate-500">AIMPF oracle cost gap: {(run.baseline_comparison?.aimpf_oracle_cost_gap*100).toFixed(1)}%</p>
        </div>}
        {run?.error&&<p className="mt-4 text-rose-300">{run.error}</p>}
      </Card>
    </div>
    <Card className="mt-5"><h2 className="font-semibold">Registered experiments</h2><div className="mt-4 space-y-2">{rows.map(r=><div key={r.id} className="rounded-xl border border-slate-800 p-3"><div className="flex items-start justify-between gap-3"><div className="font-medium">{r.name}</div>{r.result&&<span className="text-xs text-cyan-300">baseline comparison</span>}</div><div className="mt-1 text-sm text-slate-400">{r.hypothesis}</div>{r.result?.baseline_comparison&&<div className="mt-2 text-xs text-slate-500">Oracle gap {(r.result.baseline_comparison.aimpf_oracle_cost_gap*100).toFixed(1)}% · {r.result.baseline_comparison.strategies.length} strategies</div>}</div>)}</div></Card>
  </main>
}
