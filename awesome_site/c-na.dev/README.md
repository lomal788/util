# c-na.dev 보관본

https://www.c-na.dev/ (Sina Gholizadeh 포트폴리오)를 2026-11-09에 통째로 저장한 것이다.

## 여는 법

`열기.bat` 을 더블클릭하면 로컬 서버가 뜨고 브라우저에서 http://localhost:8787/ 이 열린다. 창을 닫으면 서버도 꺼진다.
인터넷 없이 열린다. Node.js 가 필요하다.

Next.js 사이트라서 `site/` 의 HTML을 직접(file://) 열면 화면이 깨진다. 반드시 서버로 연다.

## 들어 있는 것

| 위치 | 내용 |
|---|---|
| `site/` | 받은 파일 원본 그대로 (HTML·JS·CSS·폰트·이미지·효과음·3D 텍스처·`resume.pdf`) |
| `site/manifest.json` | 요청 URL(쿼리 포함) → 저장 파일 대응표 |
| `snapshots/` | 페이지별 전체 화면 캡처(데스크톱·모바일 PNG)와 렌더된 HTML |
| `tools/mirror.js` | 크롤러. 페이지를 돌며 끝까지 스크롤하고 받은 응답을 전부 저장 |
| `tools/fetch_missing.js` | 클릭·게임 중에만 쓰이는 자원(효과음, 원본 이미지 등)을 코드 안 문자열에서 찾아 받음 |
| `tools/serve.js` | 오프라인 서버. `FILL=1` 로 띄우면 없는 파일을 원본 사이트에서 받아 채운다 |
| `tools/fill_explore.js` | 채우기 모드 서버에 WebGL 브라우저로 붙어 `/explore` 3D 장면을 눌러 보며 모델·텍스처를 채움 |
| `tools/check_offline.js` | 외부 접속을 막고 각 페이지를 열어 빠진 자원을 세는 검사 |

페이지: `/`, 3D 책상 `/explore`(메인의 "Explore desk"), 작업 소개 7개(`/works/giftbede`, `iconly-pro`, `campaign-lark`, `solsta`, `maileroo`, `wassieverse-canvas`, `laelaps`), 게임 5개(`/tank`, `/space-invader`, `/tetris`, `/pac-man`, `/snake`).

## 원본과 다른 점

- `/tank` 의 3D 모델 해제기(Draco)는 원래 `www.gstatic.com` 에서 받는다. 사본은 `site/_ext/www.gstatic.com/` 에 있고, `serve.js` 가 JS를 보낼 때만 주소를 로컬로 바꾼다. 저장 파일은 바꾸지 않았다.
- `/_next/image` 는 저장할 때 받은 폭만 있다. 다른 폭을 요청하면 원본 이미지로 응답한다.
- Cloudflare 방문 통계 스크립트는 받지 않는다.
- 사이트 안 링크로 이동할 때 미리 받아 둔 데이터가 없으면 페이지를 새로 불러온다. 화면은 같다. 이때 콘솔에 `?_rsc=... 404` 가 찍히는 것은 정상이다.
- POST(Vercel·Cloudflare 방문 통계)는 받은 척만 한다(204).

## 빠진 파일이 보이면

코드가 경로를 이어 붙여 부르는 파일(`/models/${이름}.glb` 등)은 미리 다 알 수 없다. 콘솔에 404가 보이면 인터넷이 될 때 채우기 모드로 한 번 열어 그 화면을 돌아다니면 된다.

```
set FILL=1
node tools\serve.js
```

받은 파일은 `site/` 와 `manifest.json` 에 바로 더해진다. 다음부터는 `열기.bat` 으로 연다.

## 다시 받기

```
cd tools
npm i
node mirror.js
node mirror.js /explore
node fetch_missing.js
```

그다음 `FILL=1` 서버를 띄우고 `node fill_explore.js` 를 돌린다. Git Bash에서는 `/explore` 가 Windows 경로로 바뀌므로 `MSYS_NO_PATHCONV=1` 을 앞에 붙인다.
