import React,{createContext,useContext,useState,useEffect,useMemo,useCallback,useRef} from 'react';
import {api,safeGet,safeSet} from './api';
const Context=createContext(null);
export const useTwin=()=>useContext(Context);
export function TwinProvider({children}){
 const selectionGeneration=useRef(0);
 const [patients,setPatients]=useState([]),[patient,setPatient]=useState(null),[cursor,setCursor]=useState(0),[prediction,setPrediction]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false),[metrics,setMetrics]=useState(null),[provenance,setProvenance]=useState(null),[card,setCard]=useState(null),[audit,setAudit]=useState(null),[view,setView]=useState(()=>safeGet('view','research')),[motion,setMotion]=useState(()=>safeGet('motion',false)),[summaries,setSummaries]=useState({}),[notice,setNotice]=useState(''),[loaded,setLoaded]=useState(false);
 const notify=useCallback(message=>{setNotice(message);},[]);
 useEffect(()=>{if(!notice)return;const id=setTimeout(()=>setNotice(''),5000);return()=>clearTimeout(id);},[notice]);
 const load=useCallback(async()=>{if(loading)return;setLoading(true);setError('');try{
  const result=await api.patients();const rows=result.patients||result;if(!Array.isArray(rows)||!rows.length)throw new Error('The documented research subset is not available yet. No synthetic substitute has been loaded.');
  setPatients(rows);const first=rows[0].series?rows[0]:await api.patient(rows[0].id);setPatient(first);setCursor(first.defaultCursor??Math.min(287,first.series.length-1));setLoaded(true);
  Promise.allSettled([api.metrics(),api.provenance(),api.card(),api.audit()]).then(r=>{if(r[0].status==='fulfilled')setMetrics(r[0].value);if(r[1].status==='fulfilled')setProvenance(r[1].value);if(r[2].status==='fulfilled')setCard(r[2].value);if(r[3].status==='fulfilled')setAudit(r[3].value);});
 }catch(e){setError(e.message);}finally{setLoading(false);}},[loading]);
 const select=useCallback(async id=>{const generation=++selectionGeneration.current;try{const p=patients.find(p=>p.id===id);if(!p)return;const full=p.series?p:await api.patient(id);if(generation!==selectionGeneration.current)return;setPrediction(null);setPatient(full);setCursor(full.defaultCursor??Math.min(287,full.series.length-1));}catch(e){if(generation===selectionGeneration.current)notify(e.message);}},[patients,notify]);
 useEffect(()=>{if(!patient)return;const controller=new AbortController();setBusy(true);setPrediction(null);setError('');const id=setTimeout(()=>{api.predict(patient.id,cursor,{},controller.signal).then(p=>{setPrediction(p);if(cursor===(patient.defaultCursor??287))setSummaries(s=>({...s,[patient.id]:p}));}).catch(e=>{if(e.name!=='AbortError'){setError(e.message);setPrediction(null);}}).finally(()=>{if(!controller.signal.aborted)setBusy(false);});},100);return()=>{clearTimeout(id);controller.abort();};},[patient,cursor]);
 useEffect(()=>{if(!patients.length)return;let canceled=false;const work=async()=>{for(const p of patients){if(canceled)break;if(p.prediction){setSummaries(s=>({...s,[p.id]:p.prediction}));continue;}try{const result=await api.predict(p.id,p.defaultCursor??287);if(!canceled)setSummaries(s=>({...s,[p.id]:result}));}catch{if(!canceled)setSummaries(s=>({...s,[p.id]:{abstained:true,error:'Inference unavailable'}}));}}};work();return()=>{canceled=true;};},[patients]);
 useEffect(()=>{safeSet('view',view);},[view]);useEffect(()=>{safeSet('motion',motion);document.documentElement.dataset.motion=motion?'reduced':'system';},[motion]);
 const value=useMemo(()=>({patients,patient,cursor,setCursor,prediction,loading,error,busy,metrics,provenance,card,audit,view,setView,motion,setMotion,summaries,notice,notify,loaded,load,select}),[patients,patient,cursor,prediction,loading,error,busy,metrics,provenance,card,audit,view,motion,summaries,notice,notify,loaded,load,select]);
 return <Context.Provider value={value}>{children}</Context.Provider>;
}
