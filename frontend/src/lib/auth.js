import {request,safeGet,safeSet} from './api';
let client,config,rememberMode=safeGet('remember-auth',true);
export async function authConfig(){if(!config)config=await request('/api/auth/config');return config;}
const storage={
 getItem:key=>(rememberMode?localStorage:sessionStorage).getItem(key),
 setItem(key,value){(rememberMode?localStorage:sessionStorage).setItem(key,value);(rememberMode?sessionStorage:localStorage).removeItem(key);},
 removeItem(key){localStorage.removeItem(key);sessionStorage.removeItem(key);}
};
export async function authClient(remember){const c=await authConfig();if(!c.enabled)throw new Error('Workspace authentication is not connected. Research demo access remains available.');if(typeof remember==='boolean'){rememberMode=remember;safeSet('remember-auth',remember);}if(!client){const {createClient}=await import('@supabase/supabase-js');client=createClient(c.supabaseUrl,c.publishableKey,{auth:{persistSession:true,storage,autoRefreshToken:true,detectSessionInUrl:true,flowType:'pkce'}});}return client;}
