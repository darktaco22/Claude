// GLB loading with a cache, skinned-safe cloning, and the units' metadata (assets/units/units.json).
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone as skClone} from 'three/addons/utils/SkeletonUtils.js';

const loader = new GLTFLoader();
const cache = new Map();
export let progress = {done: 0, total: 0};
// 'low' while the 3D loads behind the menus (their images come first), 'auto' once a battle is waiting for it (src/main.js)
export const fetchMode = {priority: 'low'};

export function loadGLB(url) {
  if (!cache.has(url)) {
    progress.total++;
    cache.set(url, fetch(url, {priority: fetchMode.priority}).then(r => { if (!r.ok) throw new Error(`${r.status} ${url}`); return r.arrayBuffer(); })
      .then(buf => loader.parseAsync(buf, url.slice(0, url.lastIndexOf('/') + 1))).finally(() => { progress.done++; }));
  }
  return cache.get(url);
}
// a fresh copy (its own skeleton for skinned meshes); animations are shared clips
export function cloneGLB(g) { return {scene: skClone(g.scene), animations: g.animations}; }

let meta = null;
export async function unitMeta() {
  if (meta) return meta;
  try { meta = await (await fetch('assets/units/units.json')).json(); } catch { meta = {}; }
  return meta;
}
