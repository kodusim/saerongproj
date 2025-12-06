---
url: 'https://developers-apps-in-toss.toss.im/development/client/android.md'
description: >-
  React Native 앱인토스 개발을 위한 Android 환경 설정 가이드입니다. Android Studio, SDK
  Command-line Tools 설치 및 환경 변수 설정 방법을 확인하세요.
---

# Android 환경설정

React Native 개발을 위해 **Android 개발 환경 설정 방법**을 안내해요.

## 1. Android Studio 설치

React Native를 Android 환경에서 실행하려면 **Android SDK**와 [`adb`(Android Debug Bridge)](https://developer.android.com/tools/adb?hl=ko#howadbworks)가 필요해요.\
먼저, 아래 링크를 통해 Android Studio를 설치하세요.

* [Android Studio 설치 링크](https://developer.android.com/studio?hl=ko)

## 2. Android SDK Command-line Tools 설치

Android SDK Command-line Tools를 설치하려면 다음 단계를 따라 진행하세요.

1. Android Studio를 열고 상단 메뉴에서 **\[Android Studio] > \[Settings]** 를 클릭하세요.
2. 왼쪽 메뉴에서 **\[Languages & Frameworks] > \[Android SDK]** 를 선택하세요.
3. **\[SDK Tools]** 탭에서 "Android SDK Command-line Tools"를 체크하고 "OK" 버튼을 눌러 설치하세요.
   ![이미지](/assets/setup-android-adb.COp4Yig6.png)

## 3. 환경 변수 설정

`adb`를 사용하려면 환경 변수를 설정해야 해요.

### macOS

사용 중인 셸의 초기화 스크립트(`.zshrc` 또는 `.bashrc`)에 다음 내용을 추가하세요.

```bash
export ANDROID_HOME=~/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/tools/bin:$ANDROID_HOME/platform-tools
```

### Windows

#### 1. 실행 프롬프트 열기

`Windows` + `R` 키를 눌러 실행 창을 열고 `SystemPropertiesAdvanced`를 입력한 뒤 **Enter** 키를 눌러주세요.

![실행 프롬프트](/assets/setup-android-windows-1.DOFYC1J8.jpg)

#### 2. 환경 변수 메뉴로 진입하기

\[시스템 속성] 창에서 \[고급] 탭을 선택하고, 하단의 \[환경 변수] 버튼을 눌러주세요.

![환경 변수](/assets/setup-android-windows-2.BQ_BCp0c.png)

#### 3. 사용자 변수에서 `Path` 편집

사용자 변수 섹션에서 `Path` 변수를 선택한 뒤 \[편집] 버튼을 눌러주세요.

:::info
만약 `Path` 변수가 없다면, \[새로 만들기] 버튼을 눌러 새 변수를 생성하고 이름을 `Path`로 설정하면 돼요.
:::

![Path 환경 변수](/assets/setup-android-windows-3.DxEAc_wY.png)

#### 4. Android SDK 경로 추가하기

편집 창에서 \[새로 만들기] 버튼을 눌러 다음 경로를 추가하세요.

`C:\Users\{사용자명}\AppData\Local\Android\sdk\platform-tools`

여기서 `{사용자명}`은 현재 Windows 사용자 계정 이름으로 바꿔 입력해야 해요.

![환경 변수 추가](/assets/setup-android-windows-4.n8Ve7E9m.png)

***

### 설정 확인

환경 변수가 정상적으로 등록되었는지 아래 명령어로 확인하세요.

```shell
adb version
# Android Debug Bridge version 1.0.41
# Version 33.0.2-8557947
# Installed as /Users/heecheol.kim/Library/Android/sdk/platform-tools/adb
```

정상적으로 버전이 출력되면 `adb` 설정이 완료되었어요.\
자세한 내용은 [Android 공식 문서 - 환경 변수](https://developer.android.com/tools/variables?hl=ko#android_home)를 참고하세요.

## 4. 기기 연결

PC와 Android 기기를 연결하는 방법을 안내해요. 이 문서를 따라 [adb(Android Debug Bridge)](https://developer.android.com/tools/adb?hl=ko#howadbworks)를 사용해서 기기와 통신할 수 있어요.

### 개발자 옵션 활성화

::: info

기기 제조사에 따라 개발자 옵션을 활성화하는 방법이 다를 수 있어요. 사용 중인 기기의 제조사별 가이드는 인터넷 검색으로 확인하세요.

:::

**갤럭시 기기 기준**

1. \[설정] 앱 열기
2. \[휴대전화 정보] > \[소프트웨어 정보] 메뉴로 이동
3. \[빌드 번호] 항목을 빠르게 여러번 탭하기

자세한 방법은 [삼성 지원 홈페이지](https://www.samsung.com/uk/support/mobile-devices/how-do-i-turn-on-the-developer-options-menu-on-my-samsung-galaxy-device)에서 확인할 수 있어요.

### USB 디버깅 활성화

개발자 옵션이 활성화되었다면, 이제 USB 디버깅 옵션을 활성화해 주세요.

1. \[설정] 앱을 열어주세요.
2. \[개발자 옵션] 메뉴로 이동해주세요.
3. \[USB 디버깅] 항목을 활성화 해주세요.

### PC와 기기 연결하기

USB 케이블로 PC와 기기를 연결한 뒤, 다음 명령어를 실행해 기기가 정상적으로 연결되었는지 확인해 주세요.

```shell
adb devices
# * daemon not running; starting now at tcp:5037
# * daemon started successfully
# List of devices attached
# R3CTA0BMCPK	device
```

제대로 연결되었다면 **"List of devices attached"** 아래에 기기의 디바이스 아이디가 표시돼요. 다음 예시에서는 `R3CTA0BMCPK`가 디바이스 아이디예요.

::: details 디바이스 아이디가 표시되지 않는다면?
다음 사항들을 확인해주세요.

* **USB 디버깅 활성화하기**: Android 기기에서 \[설정] > \[개발자 옵션] > \[USB 디버깅]이 활성화 되어있는지 확인해요.
* **ADB 서버 재시작하기**: `adb kill-server` 명령어를 실행한 후 다시 `adb devices` 명령어로 연결 상태를 확인해요.

:::

## 5. 에뮬레이터 설정

Android 에뮬레이터는 실제 기기처럼 동작하며, React Native 화면을 테스트할 수 있는 유용한 도구예요.

> ⚠️ 디버깅과 QA는 가능한 **실제 기기**에서 진행하는 것을 권장합니다.

### 1. Android Studio에서 에뮬레이터 추가 설정 화면 열기

Android Studio를 실행한 후 오른쪽 메뉴에서 \[Virtual Device Manager] > \[+ 버튼]을 순서대로 클릭해 주세요.

![안드로이드 스튜디오로 에뮬레이터 설정 화면 열기](/assets/setup-android-6.DIpNjcDJ.png)

### 2. 에뮬레이터 추가하기

테스트 환경은 실제 사용자 환경과 비슷하게 설정하는 게 좋아요. 아래는 "갤럭시 S23"과 비슷한 에뮬레이터를 만드는 방법이에요.

:::tip 갤럭시 S23 사양

* 디스플레이: 6.1인치
* 운영체제: API 33부터 지원 (예시에서는 API 35 사용)

:::

![안드로이드 스튜디오로 에뮬레이터 설정](/assets/setup-android-7.DHo2POTo.gif)

위 영상처럼 \[Pixel 8a] > \[VanilaIceCream (API 35)] > \[AVD Name 설정] 순으로 진행하면 에뮬레이터 설정을 완료할 수 있어요.

## 6. 에뮬레이터 실행

추가한 에뮬레이터 목록을 확인할 수 있고, 원하는 에뮬레이터를 바로 실행할 수 있어요.

### 1. Android Studio에서 에뮬레이터 목록 확인하기

Android Studio를 실행한 후 오른쪽 메뉴에서 \[Virtual Device Manager]를 클릭해 주세요.

### 2. 에뮬레이터 실행하기

실행하고자 하는 에뮬레이터를 확인한 뒤, 재생 버튼을 눌러 실행할 수 있어요.

![에뮬레이터 실행하기](/assets/setup-android-exec-emulator.BbVjs52o.png)

## 7. 앱인토스 샌드박스 앱 설치

실제 기기와 에뮬레이터에서 같은 APK 파일을 사용해요.

* [앱인토스 샌드박스 앱 다운로드](/development/test/sandbox)

### 1. Android Studio에서 설치

Android Stuido를 활용해서 실기기에 앱인토스 샌드박스 앱을 설치할 수 있어요.

1. Android Studio에서 오른쪽 메뉴의 \[Device Manager]에 연결된 기기가 표시되는지 확인해요.

![안드로이드 실행가능한 기기 목록 보여주기](/assets/setup-android-2.DXcNnBuo.png)

2. 연결된 기기의 오른쪽에 있는 \[Start Mirroring] 버튼을 클릭하면 기기 화면을 Android Studio에 표시할 수 있어요.

![안드로이드 실행가능한 기기 목록 보여주기](/assets/setup-android-3.5PFEsGIn.gif)

3. 다운로드한 앱인토스 샌드박스 앱 APK 파일을 끌고 와서 기기에 설치할 수 있어요.

![안드로이드 스튜디오로 앱 설치](/assets/setup-android-4.WhqxGp5g.gif)

### 2. `adb` 명령어로 설치

1. 터미널에서 APK 파일이 있는 폴더로 이동해요.
2. 아래 명령어로 APK 파일을 설치해요.

```shell
adb install -r -t {파일이름}
```

예를 들어, 파일 이름이 `apssintoss-debug.apk`라면 아래 명령어를 사용해요.

```shell
adb install -r -t apssintoss-debug.apk
```

![adb로 앱인토스 샌드박스 앱 다운로드](/assets/setup-android-5.DrtXEOR5.gif)
