import React,{useRef} from 'react';
import {Canvas,useFrame} from '@react-three/fiber';
import {OrbitControls,Float,Line} from '@react-three/drei';
const CYAN='#55dbf2',VIOLET='#a69aff';
function Part({position,scale,rotation=[0,0,0],wire=false}){return <mesh position={position} scale={scale} rotation={rotation}><sphereGeometry args={[1,24,24]}/><meshStandardMaterial color={wire?CYAN:'#3b8fab'} metalness={.6} roughness={.32} transparent opacity={wire?.13:.32} wireframe={wire}/></mesh>;}
function Body({active,reduced}){
 const group=useRef();
 useFrame(({clock})=>{if(group.current&&!reduced)group.current.scale.y=1+Math.sin(clock.elapsedTime*.9)*.007;});
 const shapes=[
 [[0,1.53,0],[.22,.285,.225]],[[0,1.14,0],[.105,.19,.12]],[[0,.72,0],[.42,.52,.2]],
 [[0,.17,0],[.3,.32,.19]],[[-.5,.72,0],[.105,.39,.105],[0,0,-.17]],[[.5,.72,0],[.105,.39,.105],[0,0,.17]],
 [[-.59,.16,.02],[.085,.28,.08]],[[.59,.16,.02],[.085,.28,.08]],
 [[-.61,-.14,.025],[.085,.13,.06]],[[.61,-.14,.025],[.085,.13,.06]],
 [[-.17,-.43,0],[.14,.48,.14]],[[.17,-.43,0],[.14,.48,.14]],
 [[-.18,-1.15,.005],[.095,.36,.1]],[[.18,-1.15,.005],[.095,.36,.1]],
 [[-.18,-1.49,.095],[.105,.085,.2]],[[.18,-1.49,.095],[.105,.085,.2]]];
 return <group ref={group} position={[0,-.02,0]}>{shapes.map(([position,scale,rotation],i)=><React.Fragment key={i}><Part {...{position,scale,rotation}}/><Part {...{position,scale,rotation}} wire/></React.Fragment>)}<mesh position={[active==='heart'?-.12:0,active==='heart'?.8:.37,.22]}><sphereGeometry args={[.065,24,24]}/><meshBasicMaterial color={active==='heart'?CYAN:VIOLET}/></mesh><pointLight position={[0,.35,.5]} intensity={1.5} color={VIOLET}/><Line points={[[0,-1.4,.2],[0,-.3,.25],[0,.7,.24],[0,1.2,.16]]} color={CYAN} lineWidth={1} transparent opacity={.3}/></group>;
}
function Rings(){return <group rotation={[-Math.PI/2,0,0]} position={[0,-1.59,0]}>{[.52,.72,.98].map((r,i)=><mesh key={r}><ringGeometry args={[r,r+.006,100]}/><meshBasicMaterial color={i===1?VIOLET:CYAN} transparent opacity={.35-i*.08} side={2}/></mesh>)}</group>;}
export default function TwinScene({active='metabolic',reduced=false}){
 return <Canvas camera={{position:[0,.35,4.6],fov:44}} dpr={[1,1.5]} gl={{antialias:true,alpha:true}} aria-label="Abstract human research twin; select a signal using the adjacent controls"><ambientLight intensity={.9}/><directionalLight position={[2,3,3]} intensity={2} color="#b9edff"/><directionalLight position={[-2,1,-2]} intensity={3} color="#927dff"/><Body active={active} reduced={reduced}/><Rings/><OrbitControls enableZoom={false} enablePan={false} minPolarAngle={1.25} maxPolarAngle={1.65} minAzimuthAngle={-.55} maxAzimuthAngle={.55} enableDamping/></Canvas>;
}
