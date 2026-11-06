// EscapeLab 에셋 Three.js 헬퍼 (three r186 기준, ES 모듈)
//   import * as Lab from './js/labkit-three.js';
//   const gltf = await Lab.loadGLB('models/props/SM_Printer.glb');
//   scene.add(Lab.styleLab(gltf.scene.clone()));
//   const hound = new Lab.LabCharacter(await Lab.loadGLB('models/characters/CH_Hound.glb'));
//   scene.add(hound.root); hound.play('Idle');  // 매 프레임 hound.update(dt)
//
// 단위 1 = 1 m, Y-up, 캐릭터 정면 = +Z.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';

export const STUD_M = 0.28;            // Roblox 1 스터드 = 0.28 m (Lua 쪽 수치 옮길 때)
export const studs = (s) => s * STUD_M;

const loader = new GLTFLoader();
const cache = new Map();

/** 같은 URL 은 한 번만 내려받는다. 여러 개 배치할 땐 gltf.scene.clone() (캐릭터는 LabCharacter 가 복제). */
export function loadGLB(url) {
  if (!cache.has(url)) cache.set(url, loader.loadAsync(url));
  return cache.get(url);
}

/** GLB 에 심어 둔 메타 (치수 · 판정 키 · 애니메이션 루프/우선순위 · 부착 뼈). */
export function meta(gltf) {
  return gltf.asset?.extras?.escapelab ?? {};
}

const lambertCache = new WeakMap();
function toLambert(src) {
  if (lambertCache.has(src)) return lambertCache.get(src);
  const m = new THREE.MeshLambertMaterial({
    name: src.name, map: src.map, color: src.color,
    emissive: src.emissive, emissiveMap: src.emissiveMap, emissiveIntensity: src.emissiveIntensity,
    transparent: src.transparent, opacity: src.opacity, side: src.side, alphaTest: src.alphaTest,
  });
  lambertCache.set(src, m);
  return m;
}

/**
 * 재질 · 그림자 규칙 적용 (Roblox LabKitSetup 과 같은 규칙).
 *  - M_Outline (인버티드 헐, unlit): 그림자 · 레이캐스트 끔. 앞면 컬링 그대로 둘 것 (DoubleSide 로 바꾸면 덩어리가 됨)
 *  - M_Status_* (unlit 발광색): 그림자 끔
 *  - M_Glass: 그림자 끔, depthWrite 끔
 *  - 나머지: shading='lambert'(기본, Roblox 와 가까움) | 'standard'(glTF 원본 그대로)
 */
export function styleLab(root, { shading = 'lambert', shadows = true } = {}) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    const name = o.material?.name ?? '';
    if (name === 'M_Outline') {
      o.castShadow = o.receiveShadow = false;
      o.raycast = () => {};
      o.userData.labRole = 'outline';
    } else if (name.startsWith('M_Status_')) {
      o.castShadow = o.receiveShadow = false;
      o.userData.labRole = 'status';
    } else if (name === 'M_Glass') {
      o.castShadow = false;
      o.material.depthWrite = false;
      o.renderOrder = 1;
      o.userData.labRole = 'glass';
    } else {
      o.castShadow = o.receiveShadow = shadows;
      if (shading === 'lambert' && o.material?.isMeshStandardMaterial) o.material = toLambert(o.material);
      o.userData.labRole = 'body';
    }
  });
  return root;
}

/** 캐릭터 1명 = 복제된 스킨 메시 + 믹서. 애니메이션 루프 · 1회 재생은 GLB 메타를 따른다. */
export class LabCharacter {
  constructor(gltf, styleOpts) {
    this.meta = meta(gltf);
    this.root = styleLab(cloneSkinned(gltf.scene), styleOpts);
    this.mixer = new THREE.AnimationMixer(this.root);
    this.actions = {};
    for (const clip of gltf.animations) {
      const a = this.mixer.clipAction(clip);
      const m = this.meta.anims?.[clip.name] ?? {};
      if (m.loop) a.setLoop(THREE.LoopRepeat, Infinity);
      else { a.setLoop(THREE.LoopOnce, 1); a.clampWhenFinished = true; }   // DashHitPin 등: 마지막 자세 유지
      this.actions[clip.name] = a;
    }
    this.current = null;
  }

  get names() { return Object.keys(this.actions); }

  /** 이름으로 재생. 1회 재생 애니메이션이 끝나면 'finished' 이벤트 → then 으로 다음 상태. */
  play(name, { fade = 0.15, then } = {}) {
    const next = this.actions[name];
    if (!next) throw new Error(`${this.meta.classId}: 애니메이션 없음 ${name}`);
    if (next === this.current && next.isRunning()) return next;
    next.reset().setEffectiveWeight(1).play();
    if (this.current && this.current !== next) next.crossFadeFrom(this.current, fade, false);
    this.current = next;
    if (then) {
      const onDone = (e) => {
        if (e.action !== next) return;
        this.mixer.removeEventListener('finished', onDone);
        this.play(then, { fade });
      };
      this.mixer.addEventListener('finished', onDone);
    }
    return next;
  }

  bone(name) { return this.root.getObjectByName(name); }

  /** 부착 뼈(RightGrip · LeftGrip · NeckAttach · BackAttach · BeltEquip)에 소품을 붙인다. */
  attach(boneName, obj) {
    const b = this.bone(boneName);
    if (!b) throw new Error(`${this.meta.classId}: 뼈 없음 ${boneName}`);
    b.add(obj);
    return obj;
  }

  update(dt) { this.mixer.update(dt); }
}
