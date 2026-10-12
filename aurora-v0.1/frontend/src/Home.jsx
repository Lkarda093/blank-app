import React,{useEffect,useState} from 'react';
import {Icon} from './UI.jsx';
export const providers=[
 {name:'ChatGPT',icon:'spark',color:'teal',category:'Chat',description:'Texto e código'},
 {name:'Gemini',icon:'spark',color:'blue',category:'Chat',description:'Texto e código'},
 {name:'Claude',icon:'sun',color:'coral',category:'Chat',description:'Texto e código'},
 {name:'DeepSeek',icon:'code',color:'indigo',category:'Código',description:'Texto e código'},
 {name:'Grok',icon:'spark',color:'slate',category:'Chat',description:'Conversação'},
 {name:'Perplexity',icon:'search',color:'cyan',category:'Pesquisa',description:'Pesquisa'},
 {name:'Stability AI',icon:'image',color:'violet',category:'Imagens',description:'Imagens'},
 {name:'Runway',icon:'video',color:'indigo',category:'Vídeos',description:'Vídeos'},
];
const tasks=[
 ['Chat Geral','Converse com minha IA principal','chat','violet','chat'],
 ['Pesquisar','Busque informações na web','search','teal','planned'],
 ['Analisar Arquivos','Documentos, imagens, mapas…','file','blue','planned'],
 ['Gerar Imagens','Crie fotos, mapas e diagramas','image','magenta','planned'],
 ['Gerar Vídeos','Transforme ideias em vídeos','video','pink','planned'],
 ['Programar','Crie e analise códigos','code','indigo','code'],
];
export function Clock(){
 const [now,setNow]=useState(()=>new Date());useEffect(()=>{const id=setInterval(()=>setNow(new Date()),1000);return()=>clearInterval(id);},[]);
 return <div className="clock"><Icon name="calendar" size={20}/><div><span>{now.toLocaleDateString('pt-BR',{weekday:'long',day:'numeric',month:'long',year:'numeric'})}</span><time dateTime={now.toISOString()}>{now.toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}</time></div></div>;
}
export default function Home({name,onPrompt,onPlanned,onAgents,busy,configured}){
 return <section className="home-dashboard" aria-label="Início da Aurora"><div className="home-greeting"><div><h1>Olá, {name||'bem-vindo'} <span aria-hidden="true">👋</span></h1><p>O que vamos criar hoje?</p></div><Clock/></div>
 <div className="task-grid">{tasks.map(([title,description,icon,color,kind])=><button key={title} className="task-card" disabled={busy} onClick={()=>kind==='planned'?onPlanned(title):onPrompt(kind==='code'?'Ajude-me a escrever ou revisar um código. Pergunte qual linguagem e qual é o objetivo.':'')}><span className={`feature-icon ${color}`}><Icon name={icon} size={24}/></span><span><strong>{title}</strong><small>{description}</small>{kind==='planned'&&<em>Em desenvolvimento</em>}</span></button>)}</div>
 <div className="provider-strip" aria-label="Provedores de IA">{providers.map(p=><button key={p.name} className={`provider-chip ${p.name==='Gemini'?'selected':''}`} disabled={busy} title={p.name==='Gemini'?'Configuração do servidor; o envio verifica acesso e cota.':'Em desenvolvimento · não integrado'} onClick={()=>p.name==='Gemini'?onPrompt(null):onAgents(p.name)}><span className={`provider-icon ${p.color}`}><Icon name={p.icon} size={19}/></span><span><strong>{p.name}</strong><small>{p.name==='Gemini'?(configured?'Configurado':'Não configurado'):'Não integrado'}</small></span></button>)}<button className="provider-chip more" disabled={busy} onClick={()=>onAgents('')}><Icon name="grid"/><span>Mais IAs</span></button></div>
 </section>;
}
const quickActions=[['Resumir um documento','file','blue','document'],['Analisar um mapa','map','teal','map'],['Criar um plano de estudos','study','coral','study'],['Gerar um diagrama','diagram','teal','diagram'],['Organizar meus arquivos','folder','blue','files']];
const prompts={document:'Quero resumir um documento. Ainda não posso anexar arquivos aqui; peça que eu cole o texto no chat.',map:'Quero analisar um mapa. Peça que eu descreva a área, a legenda e as informações do mapa; imagens ainda não podem ser anexadas.',study:'Ajude-me a criar um plano de estudos. Pergunte meu objetivo, os assuntos e o tempo disponível.',diagram:'Ajude-me a estruturar um diagrama em texto. Pergunte qual processo ou tema quero representar.',files:'Sugira uma estrutura para organizar meus arquivos. Pergunte quais tipos de arquivos tenho. Não execute ações no computador.'};
export function QuickActions({onPrompt,busy}) {return <div className="quick-actions" aria-label="Ações rápidas">{quickActions.map(([title,icon,color,key])=><button disabled={busy} key={key} onClick={()=>onPrompt(prompts[key])}><span className={`quick-icon ${color}`}><Icon name={icon} size={16}/></span><span>{title}</span><Icon name="arrow" size={13}/></button>)}</div>;}
