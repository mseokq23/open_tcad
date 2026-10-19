# 시작 가이드 — 4개 에이전트로 open_tcad 개발 돌리기

이 문서는 사람(레포 주인)이 읽는 안내서입니다. 에이전트용 규칙은 `CLAUDE.md`와
`docs/agent-workflow.md`에 있습니다.

## 0. 구조 한눈에 보기

```
            GitHub 이슈 = 작업 큐 (role:*, status:*, "Depends on: #n")
                                  │
 ┌──────────────┬────────────────┼──────────────────┬──────────────┐
 │ researcher   │ implementer    │ verifier         │ designer     │
 │ /role-research│ /role-implement│ /role-verify     │ /role-design │
 │ 문헌→spec·데이터│ spec→코드·단위테스트│ 2-key 확인·독립 검증│ GUI·스키마·문서 │
 └──────┬───────┴───────┬────────┴────────┬─────────┴──────┬───────┘
        └──── PR (review:verify) ─────────►│ 검토 → review:approved / review:changes
                                           └──► 사람이 머지 (또는 --auto-merge)
```

* **역할 = 스킬**: `.claude/skills/role-*/SKILL.md`. 각 세션은 `/role-<역할> <이슈번호>`로
  시작하고, 인자가 없으면 다음 일을 스스로 고릅니다.
* **문헌 정확성 장치**
  1. spec 없이는 물리 코드 금지, 모든 값·식에 `source`(references.yaml id) + `locator`(식/표/쪽).
  2. **Two-key**: 연구자가 `extracted`로 넣은 값을 검증자가 `source-checker` 서브에이전트로
     **값을 모른 채(blind)** 다시 읽어 일치할 때만 `checked`. 서브에이전트는 훅
     (`scripts/hooks/blind_read_guard.py`)으로 `literature/pdfs/` 외 레포 파일을 못 읽습니다.
  3. 실행 시 게이트: `MaterialDB.value(..., policy="strict")`는 `checked`만 허용.
  4. CI의 `scripts/check_citations.py`가 출처·locator·상태를 검사하고, 단계 게이트에서는
     `--strict`로 미확인 값·`TBD`·미검증 모델을 전부 실패 처리합니다.
* **검증 독립성**: 검증 테스트는 구현을 보지 않고 spec+문헌만으로 먼저 작성되며
  (`@pytest.mark.requires_model(...)`로 구현 전엔 skip), 구현 PR이 그 테스트를 통과해야 합니다.

## 1. 준비물 (한 번만)
| 도구 | 확인 명령 | 비고 |
|---|---|---|
| Git, GitHub 계정 | `git --version` | 레포 `mseokq23/open_tcad` 쓰기 권한 |
| uv | `uv --version` | Python 3.12 자동 설치 |
| GitHub CLI | `gh auth login` 후 `gh auth status` | 에이전트·스크립트가 이슈/PR을 다룸 |
| Claude Code | `claude --version` | 백그라운드 세션·agent view 지원 버전 |

* 권장 OS: Linux x86-64 또는 Windows + WSL2. (macOS는 MKL이 없어 `docs/known-issues.md` KI-002 참고)
* 에이전트와 GitHub 작업은 **내 컴퓨터의 Claude Code(CLI/데스크톱)와 내 `gh` 로그인**으로 합니다.
  클라우드 세션에서는 스킬이 쓰는 GitHub GraphQL이 막혀 있을 수 있고, 클라우드 세션이 GitHub에
  만든 이슈·PR·댓글에는 "via Claude" 표시가 남습니다.

## 2. 레포 받기
GitHub에 이미 올라가 있으면:
```bash
git clone https://github.com/mseokq23/open_tcad && cd open_tcad
```
처음 올릴 때(전달받은 번들 사용): GitHub에서 README·라이선스 없이 **빈 레포**를 만든 뒤
```bash
git clone open_tcad.bundle open_tcad && cd open_tcad
git remote set-url origin https://github.com/mseokq23/open_tcad.git
git push -u origin main
```
4번에서 `main` 보호를 켜면 직접 push가 막히고, 모든 변경은 PR + CI 통과로만 들어갑니다.

## 3. 로컬 동작 확인 (5분)
```bash
uv sync --extra dev
uv run opentcad info                     # DEVSIM 2.11.x, solver=mkl_pardiso
uv run pytest -q -m "not gui"            # 전부 통과해야 정상
OPENTCAD_SOLVER=umfpack uv run pytest -q -m verification
uv run python scripts/check_citations.py # 0 error (경고는 정상: 남은 숙제 목록)
```
MKL 2026이 깔려 수렴 실패가 나면 KI-001 참고(`mkl<2026` 고정, 또는 `OPENTCAD_SOLVER=umfpack`).

## 4. GitHub 설정 (중요)
> 저장소 설정 변경은 관리자 권한이 필요해 **내 컴퓨터에서** 실행합니다. 한 번만 하면 됩니다.

한 줄로 자동 설정할 수 있습니다(`gh auth login`된 관리자 계정, 다시 실행해도 안전):
```bash
uv run python scripts/bootstrap_github.py --protect --labels-only
```
설정되는 내용(수동으로 할 때도 같음):
1. **main 보호 규칙**: PR 필수 + 필수 체크 `lint`, `provenance`, `test (mkl_pardiso)`,
   `test (umfpack)`, **관리자에게도 적용**(에이전트가 내 계정으로 움직이므로 이게 실제 안전장치),
   force push·삭제 금지. 승인 리뷰 필수는 **켜지 않습니다**(같은 계정이라 자기 PR 승인 불가 →
   리뷰 결정은 라벨로 합니다).
2. **머지된 브랜치 자동 삭제**(Automatically delete head branches).
3. Actions가 켜져 있는지 확인(첫 PR에서 CI가 돌아야 함).

## 5. 백로그를 이슈로 만들기
> 새 레포에서 처음 한 번 실행합니다(이슈 #1–#82). 4번과 한 번에 하려면 `--protect`를 붙이세요.
> 백로그 YAML이 바뀌었을 때 다시 실행합니다.

```bash
uv run python scripts/bootstrap_github.py --dry-run   # 계획 확인 (라벨 30개, 마일스톤 2개, 이슈 82개)
uv run python scripts/bootstrap_github.py             # 실제 생성 (다시 돌려도 중복 생성 안 됨)
```
1단계 29개, 2단계 53개 이슈가 의존성 순서대로 만들어지고 본문에 `Depends on: #n`이 들어갑니다.
1단계만 먼저 만들려면 `--phase 1`.

## 6. Claude Code 준비
```bash
cd open_tcad
claude            # 처음 한 번: 작업공간 신뢰(trust) 대화상자 수락 → /exit
```
* `.claude/settings.json`이 `acceptEdits` 모드와 자주 쓰는 명령(uv, git, gh issue/pr, 웹검색)을
  미리 허용하고, force push·main push·merge·`rm -rf` 등은 금지합니다.
* 커밋·PR에 AI 표기(Co-Authored-By, "Generated with" 문구, 세션 링크)가 붙지 않도록
  `.claude/settings.json`의 `attribution`을 꺼 두었습니다(CLAUDE.md 규칙 7). 커밋 작성자는 내
  git 설정을 쓰므로 처음에 `git config user.name`, `git config user.email`을 확인하세요(이메일을
  공개하지 않으려면 GitHub noreply 주소 사용).
* 동시에 4세션이면 사용량이 약 4배로 빨리 소진됩니다.

## 7. 1단계 운영 — 수동 (처음 2~3일)
터미널 4개를 레포 루트에서 열고, 각각 자기 worktree에서 시작합니다. 아래 번호는 이슈가 하나도
없던 레포에 5번을 실행했을 때의 번호입니다(다르면 `scripts/orchestrate.py --status`로 확인):
```bash
claude --worktree research-1      # 입력: /role-research 1     (P1-SPEC-001)
claude --worktree implement-8     # 입력: /role-implement 8    (P1-IO-001)
claude --worktree verify-18       # 입력: /role-verify 18      (P1-VER-002)
claude --worktree design-10       # 입력: /role-design 10      (P1-SCHEMA-001)
```
번호 없이 `/role-research`처럼 입력하면 다음 작업을 스스로 고릅니다.
한 화면에서 보려면 백그라운드로:
```bash
claude --bg --name research-1 "/role-research 1"   # 백그라운드 세션은 편집 전에 자동으로 worktree로 이동
claude agents        # agent view: 상태 확인, 답장, attach
```
첫날 확인할 것: 세션이 이슈를 claim → 브랜치 → PR(`review:verify`) → 검증자 리뷰 →
`review:approved`까지 한 바퀴 도는지. 막히면 해당 세션에 직접 답하거나 SKILL.md를 고칩니다.

## 8. 2단계 운영 — 오케스트레이터
```bash
uv run python scripts/orchestrate.py --status          # 역할별 현재 작업/다음 작업, PR 대기열, 사람 할 일
uv run python scripts/orchestrate.py --dry-run --once  # 지금 무엇을 띄울지 미리보기
uv run python scripts/orchestrate.py                   # 120초마다: 역할당 1세션 유지
```
선택 규칙: ① 자기 PR 중 `review:changes` → ② (검증자) `review:verify` PR → ③ 의존성이 닫힌
`status:ready` 이슈(`priority:high` → 낮은 phase → 낮은 번호).
* 세션이 PR도 blocker 기록도 없이 끝나면 해당 이슈에 `status:needs-human`을 붙이고 알립니다.
* 같은 항목이 2번 실패하면 더 이상 띄우지 않습니다(`--max-retries`).
* 옵션: `--max-phase 1`(1단계 먼저 끝내기), `--roles verify,implement`,
  `--permission-mode auto`(요금제에서 auto 모드를 쓸 수 있을 때), `--cleanup`.

## 9. 3단계 — 자동 머지 (검증자를 신뢰하게 된 뒤)
```bash
uv run python scripts/orchestrate.py --auto-merge
```
`review:approved` + CI 전부 통과 + 충돌 없음인 PR만 squash 머지합니다. 충돌이 있으면 작성자에게
`review:changes`로 되돌립니다. 검증자 PR(`review:human`)과 단계 게이트는 항상 사람이 머지합니다.

## 10. 사람이 하는 일 (하루 10~20분)
| 언제 | 할 일 |
|---|---|
| 매일 | `review:approved`·`review:human` PR 머지 (CI 녹색 확인) |
| `status:needs-human` 알림 | 유료 논문 → `literature/pdfs/<reference-id>.pdf`로 저장(메인 체크아웃, git 추적 안 됨) / 출처 충돌 → 후보 중 결정해 코멘트 / 설계 결정 → 결정 / 멈춘 세션 → `claude attach <id>` |
| 처리 후 | `status:needs-human` 제거, `status:ready`(또는 원래 review 라벨) 다시 붙이기 |
| 백로그 변경 PR 머지 후 | `uv run python scripts/bootstrap_github.py` 다시 실행 |
| 단계 끝 | 게이트 리포트(`reports/verification/phase-<k>.md`) 검토, `check_citations.py --strict` 확인, 마일스톤 닫기 |

## 11. 개발 2단계까지의 흐름
| 단계 | 목표 | 게이트 조건(요약) | 예상 |
|---|---|---|---|
| 0 (완료) | 1D DD 코어, 검증, 에이전트 체계 | 테스트 전부 통과(두 솔버) | — |
| 1 | 2D PN 다이오드·MOS 커패시터를 GUI/CLI로 끝까지 | VER-PN-001(재검증)/PN-002/RG-001/MOS-001/MESH-001 통과, `--strict` 통과, 튜토리얼 재현 | 1.5~3개월 |
| 2 | 이동도·재결합·통계·BGN·충돌이온화·BTBT·쇼트키, 재료 세트, 수렴 자동화, AC/과도, DOE, MOSFET | 모든 2단계 VER 통과, 수렴 벤치마크 ≥95 %, `--strict` 통과 | 3~5개월 |

세부 항목과 임계 경로는 `docs/roadmap.md`, 원본 목록은 `.github/backlog/phase1.yaml`·`phase2.yaml`.
예상 기간은 검증자 처리량과 사람의 머지 속도에 가장 크게 좌우됩니다.

## 12. 문제 해결
| 증상 | 원인/해결 |
|---|---|
| `Workspace not trusted` (오케스트레이터 디스패치 실패) | 레포 루트에서 `claude` 한 번 실행해 신뢰 수락 |
| 세션이 `blocked` | 허용 목록에 없는 명령의 권한 요청. agent view에서 승인하거나 `.claude/settings.json`에 추가(designer PR) |
| `There was a floating point exception ... LU Factorization` | KI-001: mkl 2026 → `uv sync`로 `mkl<2026` 재설치, 또는 `OPENTCAD_SOLVER=umfpack` |
| PR끼리 충돌 | 작성자 PR 모드에서 `git merge origin/main`으로 해결(오케스트레이터가 자동 재배정) |
| 같은 계정이라 Approve 불가 | 정상. 리뷰 결정은 `review:*` 라벨로 함 |
| 검증자가 병목 | `--roles`로 검증자 우선 배치, 하루 한 번 PR 정리, 필요하면 연구 선행을 `--max-phase 1`로 제한 |

## 13. 바꾸고 싶을 때
* 역할 절차: `.claude/skills/role-*/SKILL.md` (designer PR로 변경, 사람이 승인)
* 권한: `.claude/settings.json`
* 백로그: `.github/backlog/*.yaml` → `scripts/bootstrap_github.py`
* 정책: `docs/literature-policy.md`, `docs/verification-policy.md`, `docs/design-guide.md`
