import React,{createContext,useContext,useEffect,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {authClient,authConfig} from './auth';

const AuthContext=createContext({session:null,config:null,loading:true,message:'',clearMessage:()=>{}});
export const useAuth=()=>useContext(AuthContext);

// Capture only callback flags. Never put authorization codes or tokens in React state.
const callbackURL=new URL(window.location.href);
const callback={code:callbackURL.searchParams.has('code'),error:callbackURL.searchParams.get('error'),hasError:callbackURL.searchParams.has('error')||callbackURL.searchParams.has('error_code')||callbackURL.searchParams.has('error_description'),recovery:callbackURL.searchParams.get('recovery')==='1'};
function clearCallbackQuery(){
 const url=new URL(window.location.href);
 for(const key of ['code','error','error_code','error_description','recovery','sb_flow_id'])url.searchParams.delete(key);
 window.history.replaceState(window.history.state,'',url.toString());
}

export function AuthProvider({children}){
 const navigate=useNavigate();
 const [session,setSession]=useState(null),[config,setConfig]=useState(null),[loading,setLoading]=useState(true),[message,setMessage]=useState('');
 useEffect(()=>{
  let active=true,subscription;
  async function start(){
   try{
    const configuration=await authConfig();
    if(!active)return;
    setConfig(configuration);
    if(!configuration.enabled)return;
    const client=await authClient();
    if(!active)return;
    // The SDK exchanges the PKCE code once during initialization, using its stored verifier.
    // The listener updates UI only; do not await another SDK operation inside this callback.
    subscription=client.auth.onAuthStateChange((event,next)=>{
     if(!active)return;
     setSession(next);
     if(event==='PASSWORD_RECOVERY'){clearCallbackQuery();navigate('/reset',{replace:true});}
    }).data.subscription;
    const initialized=await client.auth.initialize();
    const result=await client.auth.getSession();
    if(!active)return;
    setSession(result.data.session);
    const unconsumedCode=callback.code&&new URL(window.location.href).searchParams.has('code');
    if(callback.hasError||initialized.error||result.error||unconsumedCode){
     setMessage(callback.error==='access_denied'?'Sign-in was cancelled or denied. You can try again or enter demo mode.':'Sign-in could not be completed. Start a fresh sign-in from this browser, or enter demo mode.');
     clearCallbackQuery();
     if(callback.code||callback.hasError||callback.recovery)navigate('/login',{replace:true});
    }else if(callback.recovery){
     clearCallbackQuery();
     if(result.data.session)navigate('/reset',{replace:true});
     else{setMessage('This recovery link is no longer usable. Request a fresh link from the sign-in screen.');navigate('/login',{replace:true});}
    }
   }catch{
    if(active)setMessage('Account services could not be reached. The research demo remains available.');
   }finally{if(active)setLoading(false);}
  }
  start();
  return()=>{active=false;subscription?.unsubscribe();};
 },[]);
 return <AuthContext.Provider value={{session,config,loading,message,clearMessage:()=>setMessage('')}}>{children}</AuthContext.Provider>;
}
