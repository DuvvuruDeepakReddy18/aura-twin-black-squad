import React,{lazy,Suspense,useState,useEffect,Component} from 'react';
import {Heart,Activity,Moon,ScanLine,Box,RotateCcw} from 'lucide-react';
import {num,finite} from '../lib/api';
const Scene=lazy(()=>import('./TwinScene'));
class SceneBoundary extends Component{state={failed:false};static getDerivedStateFromError(){return {failed:true};}render(){return this.state.failed?this.props.fallback:this.props.children;}}
export function TwinFallback(){return <div className="twin-fallback"><svg viewBox="0 0 250 460" aria-label="2D human twin schematic"><defs><linearGradient id="bodyFill" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#22d3ee" stopOpacity=".3"/><stop offset="1" stopColor="#7c3aed" stopOpacity=".08"/></linearGradient></defs><ellipse cx="125" cy="72" rx="26" ry="34"/><path d="M113 104v20c-30 0-43 15-47 43l-11 97q0 17 14 10l18-95 9 92-12 128q-2 24 17 19l24-116 24 116q19 5 17-19l-12-128 9-92 18 95q14 7 14-10l-11-97q-4-43-47-43v-20" fill="url(#bodyFill)"/><path d="M125 125v159M100 180l25 18 25-18M95 257l30 20 30-20" strokeDasharray="3 5"/><circle cx="125" cy="224" r="9" className="core"/><ellipse cx="125" cy="432" rx="76" ry="14"/><ellipse cx="125" cy="432" rx="105" ry="24"/></svg><span>2D twin view</span></div>;}
export default function DigitalTwin({prediction,reduced=false,hero=false}){
 const [active,setActive]=useState('metabolic'),[webgl,setWebgl]=useState(false),[mode,setMode]=useState('3d'),[systemReduced,setSystemReduced]=useState(false);
 useEffect(()=>{const mq=window.matchMedia('(prefers-reduced-motion: reduce)');setSystemReduced(mq.matches);const listener=e=>setSystemReduced(e.matches);mq.addEventListener('change',listener);try{const canvas=document.createElement('canvas');setWebgl(!!(canvas.getContext('webgl2')||canvas.getContext('webgl')));}catch{}return()=>mq.removeEventListener('change',listener);},[]);
 const c=prediction?.current||{};
 const signals=[{id:'heart',label:'Heart',icon:Heart,value:finite(c.hr)?`${num(c.hr)} bpm`:'No signal loaded',detail:'Recorded heart-rate stream'},{id:'metabolic',label:'Metabolic',icon:ScanLine,value:finite(c.glucose)?`${num(c.glucose)} mg/dL`:'CGM context',detail:'Glucose and model trajectory'},{id:'activity',label:'Activity',icon:Activity,value:finite(c.activity)?num(c.activity,2):'Unavailable',detail:finite(c.activity)?'Source-defined activity measure':'Activity is not included in this subset'},{id:'rest',label:'Recovery',icon:Moon,value:'Not measured',detail:'No sleep-stage labels in this source'}];const current=signals.find(s=>s.id===active);
 return <div className={`digital-twin ${hero?'hero-twin':''}`}>
   <div className="twin-grid"/><div className="twin-orbit orbit-one"/><div className="twin-orbit orbit-two"/>
   <div className="twin-scene"><SceneBoundary fallback={<TwinFallback/>}>{webgl&&mode==='3d'?<Suspense fallback={<TwinFallback/>}><Scene active={active} reduced={reduced||systemReduced}/></Suspense>:<TwinFallback/>}</SceneBoundary></div>
   <div className="twin-coordinate coordinate-top">AURA / RESEARCH TWIN <span>SCHEMATIC 01</span></div>
   <div className="twin-signal signal-left"><i/><span>{hero?'Historical context':'Heart rate'}<strong>{hero?'EHR':finite(c.hr)?`${num(c.hr)} bpm`:'Unavailable'}</strong><small>{hero?'Synthetic clinical record':'Open research data'}</small></span></div>
   <div className="twin-signal signal-right"><i/><span>{hero?'Dynamic physiology':'Glucose'}<strong>{hero?'CGM + HR':finite(c.glucose)?`${num(c.glucose)} mg/dL`:'Unavailable'}</strong><small>{hero?'Recorded wearable stream':'Open research data'}</small></span></div>
   <div className="twin-caption"><span className="pulse-dot"/> {hero?'Two streams. One inspectable view.':'Composite research twin · replay'}</div>
   {!hero&&<><div className="hotspot-controls" aria-label="Twin signal selection">{signals.map(s=><button key={s.id} className={active===s.id?'active':''} onClick={()=>setActive(s.id)} aria-label={s.label} aria-pressed={active===s.id}><s.icon size={16}/><span>{s.label}</span></button>)}</div><div className="hotspot-detail"><span>{current.label}</span><strong>{current.value}</strong><small>{current.detail}</small></div></>}
   {webgl&&<button className="twin-mode" onClick={()=>setMode(mode==='3d'?'2d':'3d')} aria-label={`Switch to ${mode==='3d'?'2D':'3D'} twin view`}><Box size={13}/>{mode==='3d'?'2D view':'3D view'}</button>}
 </div>;
}
