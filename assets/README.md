# assets/

웹 그레이박스(Three.js)에 넣을 에셋 폴더. 파일이 없는 슬롯은 색 구분 플레이스홀더로 그려진다 (CLAUDE.md §12 모델 슬롯).

## 폴더

| 폴더 | 내용 |
|---|---|
| `props/` | 프랍 모델 (.glb 권장) |
| `characters/` | 캐릭터 모델·리그 (.glb) |
| `textures/` | 텍스처 (.png / .jpg) |

## 파일 이름 = 모델 슬롯 이름

`props/<슬롯>.glb` — 예: `props/printer.glb`, `props/crate.glb`

| 슬롯 | 대상 |
|---|---|
| `printer` | 3D 프린터 |
| `printer_base` | 프린터 받침대 (0.85m / 0.6m) |
| `crate` | 플라스틱 상자 |
| `tool_battery` · `tool_coil` · `tool_ln2` | 무력화 재료 (축전지 · 자성 코일 · 액체질소 캡슐) |
| `vent` | 벤트 패드 |
| `exit` | 탈출구 문 |
| `shelf` | 선반 |
| `barrier` | 장벽 (컨테이너 · 사물함) |

`characters/<슬롯>.glb` — `survivor`, `tagger`

## 규격

- 단위 1 = 1m, 원점 = 바닥 중앙, +Y 위
- 외곽선용 인버티드 헐 메쉬가 있으면 메쉬 이름 끝에 `_Outline`
