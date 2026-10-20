import React,{useEffect,useRef} from 'react';
import {Activity,ArrowUpRight,ArrowRight,ShieldCheck,X,LoaderCircle,AlertTriangle,Layers3,ChevronRight} from 'lucide-react';
export function Logo({compact=false}){return <span className="brand"><span className="brand-mark"><span/><span/><span/></span><span>AURA<span className="brand-twin"> TWIN</span>{!compact&&<small>Patient intelligence</small>}</span></span>;}
export function Badge({children,tone='muted',dot=false}){return <span className={`badge ${tone}`}>{dot&&<i/>}{children}</span>;}
export function Source({type='model'}){const names={ehr:'Synthetic EHR',wearable:'Open research data',derived:'Derived feature',model:'Model output',replay:'Research replay'};return <span className={`source ${type}`}>{names[type]||type}</span>;}
export function Button({children,variant='primary',icon:Icon,...props}){return <button className={`button ${variant}`} {...props}>{Icon&&<Icon size={16}/>} {children}</button>;}
export function Card({children,className='',id}){return <section id={id} className={`card ${className}`}>{children}</section>;}
export function CardHead({eyebrow,title,children,icon:Icon}){return <div className="card-head"><div>{eyebrow&&<span className="eyebrow">{eyebrow}</span>}<h2>{Icon&&<Icon size={19}/>} {title}</h2></div>{children}</div>;}
export function PageHead({eyebrow,title,description,children}){return <header className="page-head"><div><span className="eyebrow">{eyebrow||'Research workspace'}</span><h1>{title}</h1>{description&&<p>{description}</p>}</div><div className="page-actions">{children}</div></header>;}
export function Empty({title='Not yet available',children,action,error=false}){return <div className={`empty ${error?'error':''}`}>{error?<AlertTriangle size={27}/>:<Layers3 size={27}/>}<h3>{title}</h3><p>{children}</p>{action}</div>;}
export function Loading({text='Synchronizing research twin…'}){return <div className="loading"><LoaderCircle className="spin" size={24}/><span>{text}</span></div>;}
export function Stat({label,value,unit,detail,tone,source}){return <div className={`stat ${tone||''}`}><span>{label}</span><strong>{value}<small>{unit}</small></strong>{detail&&<p>{detail}</p>}{source&&<Source type={source}/>}</div>;}
export function Notice({children,tone='amber',title}){return <div className={`notice ${tone}`}><ShieldCheck size={18}/><div>{title&&<strong>{title}</strong>}<p>{children}</p></div></div>;}
export function Modal({title,children,onClose,wide=false}){
 const ref=useRef(null);useEffect(()=>{const previous=document.activeElement;ref.current?.showModal();const listener=e=>{e.preventDefault();onClose();};ref.current?.addEventListener('cancel',listener);return()=>{ref.current?.removeEventListener('cancel',listener);previous?.focus?.();};},[]);
 return <dialog ref={ref} className={`modal ${wide?'wide':''}`} aria-label={title}><header><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X/></button></header><div className="modal-body">{children}</div></dialog>;
}
export function JsonView({data,label='Inspect machine-readable record'}){return <details className="json-view"><summary>{label}<ChevronRight size={16}/></summary><pre>{JSON.stringify(data,null,2)}</pre></details>;}
export function Footer(){return <footer className="app-footer"><span>AURA TWIN <i/> History. Physiology. Foresight.</span><span>Research prototype · Not for diagnosis or treatment</span></footer>;}
