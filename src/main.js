// 진입점. W0: 빈 three 씬만 띄운다 (배경 = CLAUDE.md §12 배경색).
// W7부터 generate → buildWorld → 렌더, W8부터 플레이 루프가 여기로 들어온다.
import * as THREE from 'three';

const BG = 0x0e1013; // §12 배경·안개 색. W1에서 렌더 상수로 옮긴다.

const app = document.getElementById('app');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(BG);

const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 400);
camera.position.set(0, 60, 80);
camera.lookAt(0, 0, 0);

function resize() {
  const w = app.clientWidth, h = app.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

renderer.setAnimationLoop(() => renderer.render(scene, camera));
