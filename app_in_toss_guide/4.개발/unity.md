---
url: 'https://developers-apps-in-toss.toss.im/porting_tutorials/unity.md'
description: Unity 게임을 앱인토스 미니앱으로 포팅하는 가이드입니다. Unity WebGL 빌드 및 앱인토스 연동 방법을 확인하세요.
---

# Unity 포팅

앱인토스에 Unity 게임을 배포하려면, Unity 프로젝트를 **WebGL**로 빌드해야해요.\
이 가이드는 Unity에서 WebGL 빌드를 만드는 기본적인 방법을 안내해요.

## 1. WebGL 모듈 설치

Unity Hub에서 WebGL 플랫폼이 설치되어 있어야 해요.

1. Unity Hub 실행
2. Installs 탭 선택
3. 사용 중인 Unity 버전 옆의 점 세 개(···) 클릭 → Add Modules
4. WebGL Build Support 체크 → 설치
5. 설치가 완료되면 Unity에서 File > Build Settings로 진입했을 때 플랫폼 목록에 **WebGL**이 나타나요.

![](/assets/build_webgl.BaliDsvc.png)

## 2. 플랫폼 전환

1. Unity 프로젝트 열기
2. File > Build Settings 이동
3. WebGL 선택 → Switch Platform 클릭

## 3. Player 설정 조정

Edit > Project Settings > Player 메뉴에서 다음 항목을 설정해 주세요.

* Publishing Settings
  * Compression Format: **Disabled**로 설정

::: info 참고하세요
Compression Format이 Brotli로 설정되어 있으면, 일부 브라우저나 서버에서 압축을 해제하지 못할 수 있어요.\
로컬에서 개발할때는 Disabled 사용을 권장해요.
:::

## 4. 빌드하기

1. File > Build Settings로 이동
2. WebGL 선택된 상태에서 → Build 클릭
3. 출력 폴더 지정 (예: Build/)

## 5. 결과물 확인

빌드가 완료되면 보통 `index.html`, `Build`, `TemplateData` 폴더가 생성돼요.\
Unity 프로젝트 설정이나 버전에 따라 생성되는 폴더는 조금 다를 수 있어요.\
이 폴더들을 Vite 프로젝트에 포함해 웹페이지 형태로 띄울 수 있어요.

Vite로 Unity WebGL을 감싸는 방법은 [Vite로 Unity WebGL 감싸기](./vite_unity.md)를 참고해 주세요.

::: info 참고하세요
Unity 6000.1.8 미만 버전에서는 2D 물리 엔진(Rigidbody2D) 사용 시 WebGL 빌드에서 **GC 메모리 누수 이슈**가 있었어요.\
자세한 내용은 [Unity Discussions 포럼](https://discussions.unity.com/t/memory-leak-when-using-rigidbody2d-physics-in-webgl/1649803)에서 확인할 수 있어요.

:::
