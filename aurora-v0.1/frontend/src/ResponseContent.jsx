import React,{useState} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
export function CopyButton({text,label='Copiar resposta'}){
 const [status,setStatus]=useState('');
 return <button className="subtle" onClick={async()=>{try{await navigator.clipboard.writeText(text);setStatus('Copiado');}catch{setStatus('Não foi possível copiar; selecione o texto.');}}}>{status||label}</button>;
}
function CodeBlock({children}){
 const value=React.isValidElement(children)?String(children.props.children||''):String(children||'');
 return <div className="code-block"><CopyButton text={value} label="Copiar código"/><pre>{children}</pre></div>;
}
export default function ResponseContent({text}){
 return <div className="markdown"><Markdown remarkPlugins={[remarkGfm]} skipHtml urlTransform={url=>/^https?:\/\//i.test(url)?url:''} components={{pre:CodeBlock,a:({href,children})=>href?<a href={href} target="_blank" rel="noreferrer noopener">{children}</a>:<span>{children}</span>,img:({alt})=><span>[Imagem: {alt||'não carregada'}]</span>,table:({children})=><div className="table-scroll"><table>{children}</table></div>}}>{text}</Markdown></div>;
}
