import './globals.css'
import type {ReactNode} from 'react'
import Link from 'next/link'
import ProjectSelect from '@/components/project-select'
export default function RootLayout({children}:{children:ReactNode}){return <html lang="en"><body><header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur"><div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-4"><Link href="/" className="font-semibold tracking-wide">AIMPF</Link><nav className="flex flex-wrap items-center gap-4 text-sm text-slate-300"><Link href="/projects">Projects</Link><Link href="/changes">Changes</Link><Link href="/validation">Validation</Link><Link href="/evaluations">Evaluations</Link><Link href="/prompts">Prompts</Link><Link href="/experiments">Experiments</Link><Link href="/login">Account</Link><ProjectSelect/></nav></div></header>{children}</body></html>}
