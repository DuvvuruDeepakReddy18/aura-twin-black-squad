import React,{Suspense,lazy,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {HashRouter,Routes,Route,Navigate,useLocation} from 'react-router-dom';
import {TwinProvider} from './lib/store';
import {safeGet} from './lib/api';
import {Loading} from './components/UI';
import Shell from './components/Shell';
import Landing from './pages/Landing';
import CommandCenter from './pages/CommandCenter';
import TwinWorkspace,{PatientRecord} from './pages/TwinWorkspace';
import Timeline from './pages/Timeline';
import Replay from './pages/Replay';
import Scenario from './pages/Scenario';
import Auth,{Onboarding} from './pages/Auth';
import Settings from './pages/Settings';
import './styles.css';
function RouteReset(){const {pathname}=useLocation();useEffect(()=>{window.scrollTo({top:0,left:0,behavior:'instant'});},[pathname]);return null;}
const Evidence=lazy(()=>import('./pages/Evidence'));
const Trust=lazy(()=>import('./pages/Trust'));
document.documentElement.dataset.theme=safeGet('theme','light');
class AppBoundary extends React.Component{state={error:null};static getDerivedStateFromError(error){return {error};}render(){return this.state.error?<div className="fatal-error"><h1>The workspace could not render.</h1><p>No model values have been substituted. Reload to reconnect with the research service.</p><button className="button primary" onClick={()=>location.reload()}>Reload workspace</button><pre>{this.state.error.message}</pre></div>:this.props.children;}}
createRoot(document.getElementById('root')).render(<AppBoundary><HashRouter><RouteReset/><TwinProvider><Suspense fallback={<Loading/>}><Routes><Route path="/" element={<Landing/>}/><Route path="/login" element={<Auth/>}/><Route path="/signup" element={<Auth signup/>}/><Route path="/reset" element={<Auth recover/>}/><Route path="/onboarding" element={<Onboarding/>}/><Route path="/trust" element={<Trust standalone/>}/><Route path="/app" element={<Shell/>}><Route index element={<CommandCenter/>}/><Route path="patients" element={<CommandCenter list/>}/><Route path="twin" element={<TwinWorkspace/>}/><Route path="record" element={<PatientRecord/>}/><Route path="timeline" element={<Timeline/>}/><Route path="physiology" element={<Timeline physiology/>}/><Route path="forecast" element={<TwinWorkspace forecastOnly/>}/><Route path="scenarios" element={<Scenario/>}/><Route path="replay" element={<Replay/>}/><Route path="robustness" element={<Replay lab/>}/><Route path="evidence" element={<Evidence/>}/><Route path="trust" element={<Trust/>}/><Route path="settings" element={<Settings/>}/></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Suspense></TwinProvider></HashRouter></AppBoundary>);
