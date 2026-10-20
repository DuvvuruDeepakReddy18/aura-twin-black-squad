export async function request(path, options={}) {
  const response=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers}});
  let body;try{body=await response.json();}catch{throw new Error('The data service returned an unreadable response.');}
  if(!response.ok)throw new Error(body.error||`The data service returned ${response.status}.`);
  return body;
}
export const api={
  patients:()=>request('/api/research/patients'),
  patient:id=>request(`/api/research/patients/${encodeURIComponent(id)}`),
  predict:(patientId,cursor,scenario={},signal)=>request('/api/research/predict',{method:'POST',body:JSON.stringify({patientId,cursor}),signal}),
  metrics:()=>request('/api/research/metrics'),
  provenance:()=>request('/api/data/provenance'),
  card:()=>request('/api/model/card'),
  audit:()=>request('/api/model/audit'),
  modes:()=>request('/api/research/challenge/modes'),
  freeze:(patientId,cursor,mode)=>request('/api/research/challenge',{method:'POST',body:JSON.stringify({patientId,cursor,mode})}),
  reveal:(challengeId,challengeToken)=>request('/api/research/challenge/reveal',{method:'POST',body:JSON.stringify({challengeId,challengeToken})}),
};
export const finite=x=>typeof x==='number'&&Number.isFinite(x);
export const num=(x,n=0)=>finite(x)?x.toLocaleString('en-US',{maximumFractionDigits:n,minimumFractionDigits:n}):'—';
export function percent(x,n=1){if(!finite(x))return 'Unavailable';if(x>0&&x<.001)return '<0.1%';if(x<1&&x>.999)return '>99.9%';return `${num(x*100,n)}%`;}
export const time=t=>t?new Date(t).toLocaleTimeString('en-GB',{timeZone:'UTC',hour:'2-digit',minute:'2-digit'}):'Unavailable';
export const stamp=t=>t?new Date(t).toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'})+' research time':'Unavailable';
export const mean=values=>{const v=values.filter(finite);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;};
export const patientName=p=>p?.name||p?.id||'Select a research twin';
export const alertTriggered=p=>p?.alert===true||p?.alert?.triggered===true;
export function twinState(p){if(!p)return {label:'Loading',tone:'muted'};if(p.abstained||p.available===false||!p.forecast?.length)return {label:'Forecast withheld',tone:'amber'};if(alertTriggered(p))return {label:'Review',tone:'coral'};if(['degraded','reduced'].includes(p.quality?.status))return {label:'Attention',tone:'amber'};return {label:'Below review threshold',tone:'cyan'};}
export const eventText=p=>{const target=p?.eventDefinition||p?.predictionContract?.target||p?.contract?.target;return typeof target==='string'?target:target?.description||target?.definition||target?.label||'See the model contract for the evaluated target.';};
export function download(data,name,type='application/json'){const blob=new Blob([type==='application/json'?JSON.stringify(data,null,2):data],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export const safeGet=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(`aura:${key}`))??fallback;}catch{return fallback;}};
export const safeSet=(key,value)=>{try{localStorage.setItem(`aura:${key}`,JSON.stringify(value));return true;}catch{return false;}};



export const auditStamp=t=>t?new Date(t).toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'})+' UTC':'Unavailable';
