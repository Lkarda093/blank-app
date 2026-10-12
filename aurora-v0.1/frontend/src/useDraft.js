import {useEffect,useRef,useState} from 'react';
export function readDraftStore(scope){try{return JSON.parse(localStorage.getItem('aurora-drafts-'+scope))||{items:{},last:null};}catch{return {items:{},last:null};}}
export default function useDraft(scope){
 const [draft,render]=useState(''),[warning,setWarning]=useState('');
 const current=useRef({scope:null,key:'new'});
 function write(data){if(!current.current.scope)return;try{localStorage.setItem('aurora-drafts-'+current.current.scope,JSON.stringify(data));setWarning('');}catch{setWarning('Não foi possível salvar o rascunho neste navegador.');}}
 useEffect(()=>{current.current={scope,key:'new'};render(scope?readDraftStore(scope).items?.new||'':'');},[scope]);
 function setDraft(value){const data=readDraftStore(current.current.scope);data.items||={};if(value)data.items[current.current.key]=value;else delete data.items[current.current.key];write(data);render(value);}
 function selectDraft(key,transfer=false){const data=readDraftStore(current.current.scope);data.items||={};if(transfer){data.items[key]=data.items[current.current.key]||'';delete data.items[current.current.key];}current.current.key=key||'new';data.last=key||null;write(data);render(data.items[current.current.key]||'');}
 function forgetDraft(key){const data=readDraftStore(current.current.scope);delete data.items?.[key];if(data.last===key)data.last=null;write(data);}
 return [draft,setDraft,selectDraft,forgetDraft,warning];
}
