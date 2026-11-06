# 웹(Three.js)용 에셋

Roblox 용 FBX 와 같은 원본(.blend)에서 다시 뽑은 **glTF 바이너리(.glb)**. 모양 · 피벗 · 아틀라스는 Roblox 판과 같고, 단위 · 축 · 재질만 웹 기준으로 바꿨다.
three.js **r186 (0.186.1)** 에서 로딩 · 애니메이션 · 치수를 검증했다 (7장).

## 1. 폴더 구조

```
Web/
  models/
    props/<Name>.glb           소품 41종 (Assets/fbx 와 1:1)
    props/index.json           소품별 치수 · 원본 .blend · 트라이 수
    characters/CH_<ClassId>.glb   캐릭터 5종 = 메시 + 뼈 + 애니메이션 전부 한 파일
    characters/export_report.json
  js/labkit-three.js           로더 · 재질 규칙 · 캐릭터 애니메이션 헬퍼 (ES 모듈)
  viewer.html                  에셋 뷰어 (캐릭터 애니메이션 재생 · 소품 치수 확인)
  preview/                     Three.js 검증 시트 · 검증 결과 JSON
  src/                         재생성 스크립트 (Blender 5.x bpy)
```

## 2. 규격

| 항목 | 값 |
|---|---|
| 단위 | **1 = 1 m** (스터드 × 0.28 을 메시 · 뼈 · 위치 키에 구워 넣음. 노드 스케일 없음) |
| 축 | Y-up. 캐릭터 정면 = **+Z** |
| 피벗 | Roblox FBX 와 같음. 바닥 놓는 물건 = 바닥 중심, 천장 램프 · 벤트 해치 · 방향 화살표 등은 각자 피벗 (`index.json` 의 `minY_m` 참고) |
| 텍스처 | GLB 안에 내장 (PNG). 소품 · 생존자 = `T_Lab_Palette` 256, 술래 = `T_CH_<Id>` 512 |
| 캐릭터 | 정점당 뼈 영향 최대 2, 뼈 전부 포함(부착 뼈 포함), 30 fps 매 프레임 샘플 |
| 메타 | 각 GLB 의 `asset.extras.escapelab` 에 치수 · 판정 키 · 애니메이션 루프/우선순위 · 부착 뼈. 헬퍼의 `Lab.meta(gltf)` 로 읽음 |

## 3. 재질

| glTF 재질 | 내용 | Three.js 에서 |
|---|---|---|
| `M_LabRoblox` | 기본색 아틀라스 + 발광 마스크(×1.6), 거칠기 1 · 금속 0 | 기본 `MeshStandardMaterial`. 헬퍼가 `MeshLambertMaterial` 로 바꿈 (Roblox 화면에 더 가까움) |
| `M_CH_Hound` / `M_CH_Root` | 술래 텍스처 | 위와 같음 |
| `M_Outline` | 잉크 `#1B1D20`, **unlit**, 단면 | `MeshBasicMaterial`. **앞면 컬링 유지** — 인버티드 헐이라 뒷면만 보여 외곽선이 됨. `DoubleSide` 로 바꾸면 검은 덩어리 |
| `M_Status_<색>` | 상태 발광색, unlit | `MeshBasicMaterial` (Roblox Neon 대응. 번짐이 필요하면 블룸 후처리) |
| `M_Glass` | `#9FC3CC` 알파 0.2, 양면 | 투명. 헬퍼가 depthWrite 끔 |
| (없음) `SM_DirArrow` | 흰 메시 1종 (Roblox 판과 같음) | 종류별 색은 코드에서 `material.color` 로 (`Leash #D63A8F` · `Printer #4FD1C5` …) |

금속 · 거칠기 맵(`Assets/tex/T_Lab_Palette_Metalness/Roughness.png`)은 **일부러 넣지 않았다.** 환경맵 없는 Three.js 씬에서 금속 1 은 검게 나온다. 반사가 필요하면 환경맵을 깔고 직접 연결할 것.
바닥 · 벽 타일(`T_Tile_*`)은 GLB 가 아니라 맵 코드가 쓰는 텍스처라 `Assets/tex/` 의 PNG 를 그대로 쓰면 된다 (`texture.wrapS = wrapT = RepeatWrapping`).

## 4. 사용법

```js
import * as THREE from 'three';
import * as Lab from './js/labkit-three.js';

// 소품 — 같은 GLB 여러 개는 clone() (지오메트리 · 텍스처 공유)
const printer = await Lab.loadGLB('models/props/SM_Printer.glb');
scene.add(Lab.styleLab(printer.scene.clone()));        // shading: 'lambert'(기본) | 'standard'

// 캐릭터 — 인스턴스마다 new LabCharacter (스켈레톤 복제)
const rat = new Lab.LabCharacter(await Lab.loadGLB('models/characters/CH_LabRat.glb'));
scene.add(rat.root);
rat.play('Idle');
rat.play('SlideEnter', { then: 'SlideLoop' });          // 1회 재생 → 끝나면 다음
rat.attach('RightGrip', Lab.styleLab((await Lab.loadGLB('models/props/SM_Key_Exit_Half.glb')).scene.clone()));
// 렌더 루프: rat.update(dt)
```

`viewer.html` 은 `file://` 로 열면 브라우저가 GLB 로딩을 막는다. 이 폴더에서 로컬 서버를 띄워 열 것:
`npx serve .` 또는 `python -m http.server` → `http://localhost:<포트>/viewer.html`

## 5. 애니메이션

GLB 안 애니메이션 이름 = 리그 문서 이름 그대로 (`Idle`, `Walk`, … / `Dash`, `DashHitPin` …). 프레임 · 루프 · 우선순위 표는 `Characters/README.md` 4장과 같고, 같은 값이 GLB 메타에 들어 있어 헬퍼가 자동으로 루프 / 1회 재생(마지막 자세 유지)을 건다.

- **우선순위**: Roblox 의 Movement / Action 층은 Three.js 에 없다. 지금 헬퍼는 하나만 재생하며 교차 페이드한다. 상체만 덮는 동작(P1 상호작용 등)이 생기면 그때 뼈 마스크로 층을 나눈다
- **루트 모션 없음**: 이동은 코드가 캐릭터 위치를 옮기고, 애니메이션은 제자리. 바닥 높이 보정(`Root` 뼈 위치 키)만 들어 있다
- **판정 키**: 생존자 1.15 m · 술래 1.95 m (메타 `judgeHeight_m`). 충돌 캡슐은 이 값으로 만들고 메시 경계는 쓰지 말 것 (꼬리 · 팔이 흔들려 매 프레임 바뀜)

## 6. Roblox 스크립트 → 웹 이식 대응

| Roblox (`Assets/roblox/`) | 웹에서 할 일 |
|---|---|
| `LabKitSetup.lua` 재질 · 그림자 규칙 | `Lab.styleLab()` 으로 대체됨 |
| `MapDresser.lua` 배치 규칙 | 로직 그대로 JS 로 옮김. 수치는 스터드라 `Lab.studs(n)` 으로 변환 |
| `ExitController` · `VentFX` · `CollarFX` · `PrinterController` · `ArrowFX` · `PickupFX` · `ToolFX` | `Attribute` → 게임 상태 객체, `TweenService` → 직접 보간(또는 트윈 라이브러리). 연출 수치(셔터 높이 · 경광등 회전 · 흔들림 진폭)는 그대로 |
| 목줄 부착 (`CollarFX`) | `char.attach('NeckAttach', collar)` — Roblox 쪽도 같은 뼈로 고쳐야 한다는 건 `Characters/README.md` 7번 |

## 7. 검증 (three.js 0.186.1, 헤드리스 Chromium)

- **베이크**: 베이크 전후 모든 애니메이션 시작 · 중간 · 끝 프레임의 변형 정점 비교 — 최대 오차 0.04 mm
- **소품 41종**: 로딩 후 경계 상자 = 내보내기 치수 (오차 < 2 mm)
- **캐릭터 5종 × 전 애니메이션 × 전 프레임** (스킨 적용 정밀 경계):

| | 서기 최고 | 슬라이딩 | 기어가기 | 판정 키 |
|---|---|---|---|---|
| 라쿤 / 실험쥐 / 까마귀 | 1.139 / 1.138 / 1.130 | 0.571 / 0.571 / 0.576 | 0.701 / 0.701 / 0.737 | 1.15 |
| 하운드 / 루트 | 1.926 / 1.888 | — | — | 1.95 |

  Blender 검증값과 같다. 바닥은 체공 동작(`Fall` · `JumpAir`)에서만 최대 2.5 cm 아래로 내려간다 (공중이라 문제 없음).
- 결과: `preview/web_check_sheet.png`, `preview/web_closeup.png`, `preview/web_check_result.json`

## 8. 다시 뽑기

`src/` 의 세 파일을 `Assets/blender/src` 의 `labkit.py` · `rbxkit.py` 옆에 두고 실행한다. 스크립트 기준 `web/blend/` 에 소품 .blend, `web/tex/` 에 아틀라스 PNG, `out_surv/` · `out_tag/` 에 캐릭터 .blend 가 있다고 가정한다 (경로는 각 스크립트 상단 상수).

```
python3 export_glb_props.py      # 소품 .blend 10개 → models/props
python3 export_glb_chars.py      # Survivors_Rig_anims.blend · Taggers_Rig.blend → models/characters
```

Roblox 쪽 에셋을 고치면 이 GLB 도 같이 다시 뽑아야 한다 (자동 동기화 없음).
