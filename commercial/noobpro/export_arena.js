// Export the live game's arena (court, river, bridges, towers, kit, world) to a GLB with three's own GLTFExporter.
// node export_arena.js ARENA_ID OUT.glb
const {chromium}=require('playwright'); const fs=require('fs');
const [ID,OUT]=[process.argv[2]||'basement',process.argv[3]||'arena.glb'];
const GX=process.env.GX||'node_modules/three/examples/jsm/exporters/GLTFExporter.js';
(async()=>{
const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const ctx=await b.newContext({viewport:{width:430,height:860},storageState:'state.json'});
await ctx.addInitScript(()=>{try{localStorage.setItem('memeroyale.gfx','high')}catch{}});
await ctx.route('**/__gx/GLTFExporter.js',r=>r.fulfill({body:fs.readFileSync(GX,'utf8'),contentType:'text/javascript'}));
const p=await ctx.newPage(); p.on('console',m=>{const t=m.text(); if(/world|error|Error|REPORT/.test(t)) console.log('PAGE',t.slice(0,200))});
await p.goto('https://memeroyale.imaginestudio.fun/',{waitUntil:'load',timeout:90000});
await p.waitForFunction(()=>window.__game?.arena,null,{timeout:120000});
await p.waitForTimeout(8000);
const info=await p.evaluate(async(id)=>{
  const g=window.__game; g.stage._render=g.stage.render; g.stage.render=()=>{};
  await g.arena.applyTheme(id);
  await new Promise(r=>setTimeout(r,8000));
  const kids=g.arena.root.children.map(c=>c.type+':'+(c.name||'')+':'+c.children.length);
  return {kids, scene:g.stage.scene?.children.map(c=>c.type+':'+(c.name||'')).slice(0,40)};
},ID);
console.log(JSON.stringify(info).slice(0,3000));
const b64=await p.evaluate(async()=>{
  const {GLTFExporter}=await import('/__gx/GLTFExporter.js');
  const g=window.__game; const ex=new GLTFExporter();
  const T=await import('three');
  const src=g.arena.root; src.updateMatrixWorld(true);
  const root=new T.Group(); const report={inst:0,shader:[],attrs:{}};
  const KEEP=['position','normal','uv','color'];
  const cleanGeo=(geo)=>{
    const ng=new T.BufferGeometry();
    for(const k of Object.keys(geo.attributes)){
      let a=geo.attributes[k]; let name=k;
      if(k==='aCol'&&(a.itemSize===3||a.itemSize===4)) name='color';
      if(!KEEP.includes(name)){report.attrs[k]=(report.attrs[k]||0)+1; continue;}
      if(name==='color'&&!(a.itemSize===3||a.itemSize===4)) continue;
      if(name==='uv'&&a.itemSize!==2) continue;
      if(a.isInterleavedBufferAttribute) a=a.clone();
      ng.setAttribute(name,a);
    }
    if(geo.index) ng.setIndex(geo.index);
    for(const gr of geo.groups) ng.addGroup(gr.start,gr.count,gr.materialIndex);
    return ng;
  };
  const cleanMat=(m)=>{
    if(Array.isArray(m)) return m.map(cleanMat);
    if(m.isMeshStandardMaterial||m.isMeshBasicMaterial||m.isMeshPhysicalMaterial||m.isMeshLambertMaterial||m.isMeshPhongMaterial) return m;
    report.shader.push(m.name||m.type);
    const u=m.uniforms||{}; let c=new T.Color('#888888');
    for(const k of ['uMid','uColor','color','uCol','uC']) if(u[k]?.value?.isColor){c=u[k].value.clone();break;}
    const n=new T.MeshStandardMaterial({color:c, emissive:c, emissiveIntensity:0.6, roughness:0.4});
    n.name='SHADER_'+(m.name||m.type); return n;
  };
  src.traverse(o=>{
    if(!o.visible) return;
    let p=o.parent, vis=true; while(p){ if(!p.visible){vis=false;break;} p=p.parent; } if(!vis) return;
    if(o.isInstancedMesh){
      report.inst++; const geo=cleanGeo(o.geometry), mat=cleanMat(o.material); const M=new T.Matrix4();
      const n=Math.min(o.count,4000);
      for(let i=0;i<n;i++){ o.getMatrixAt(i,M); const m=new T.Mesh(geo,mat); m.name=(o.name||'inst')+'_'+i; m.matrixAutoUpdate=false; m.matrix.copy(o.matrixWorld).multiply(M); root.add(m); }
    } else if(o.isMesh){
      const m=new T.Mesh(cleanGeo(o.geometry),cleanMat(o.material)); m.name=o.name||'mesh'; m.matrixAutoUpdate=false; m.matrix.copy(o.matrixWorld); root.add(m);
    }
  });
  root.updateMatrixWorld(true);
  console.log('REPORT '+JSON.stringify(report).slice(0,1500));
  const buf=await ex.parseAsync(root,{binary:true,onlyVisible:true,maxTextureSize:2048});
  let s=''; const u=new Uint8Array(buf); for(let i=0;i<u.length;i+=0x8000) s+=String.fromCharCode.apply(null,u.subarray(i,i+0x8000)); return btoa(s);
});
fs.writeFileSync(OUT,Buffer.from(b64,'base64')); console.log('WROTE',OUT,fs.statSync(OUT).size);
await b.close();})();
