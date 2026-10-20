import {request,safeGet,safeSet} from './api';
let client,clientPromise,config,configPromise,rememberMode=safeGet('remember-auth',true);
export async function authConfig(){if(config)return config;if(!configPromise)configPromise=request('/api/auth/config').then(value=>(config=value)).catch(error=>{configPromise=null;throw error;});return configPromise;}
const storage={
 getItem:key=>(rememberMode?localStorage:sessionStorage).getItem(key),
 setItem(key,value){(rememberMode?localStorage:sessionStorage).setItem(key,value);(rememberMode?sessionStorage:localStorage).removeItem(key);},
 removeItem(key){localStorage.removeItem(key);sessionStorage.removeItem(key);}
};
export async function authClient(remember){const c=await authConfig();if(!c.enabled)throw new Error('Workspace authentication is not connected. Research demo access remains available.');if(typeof remember==='boolean'){rememberMode=remember;safeSet('remember-auth',remember);}if(!clientPromise)clientPromise=import('@supabase/supabase-js').then(({createClient})=>(client=createClient(c.supabaseUrl,c.publishableKey,{auth:{persistSession:true,storage,autoRefreshToken:true,detectSessionInUrl:true,flowType:'pkce'}}))).catch(error=>{clientPromise=null;throw error;});return clientPromise;}
