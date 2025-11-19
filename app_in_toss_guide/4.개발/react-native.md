---
url: 'https://developers-apps-in-toss.toss.im/tutorials/react-native.md'
---
# React Native

:::tip 기존 RN 프로젝트가 있는 경우
이미 React Native로 만든 서비스가 있어도 앱인토스에서 동작하려면 **Granite 기반으로 스캐폴딩** 해야 해요.\
:::

Granite을 사용해 "Welcome!"페이지가 표시되는 서비스를 만들어볼게요.\
이를 통해 로컬 서버를 연결하는 방법과 파일 기반 라우팅을 배울 수 있어요.

## 스캐폴딩

앱을 만들 위치에서 다음 명령어를 실행하세요.

이 명령어는 프로젝트를 초기화하고 필요한 파일과 디렉토리를 자동으로 생성해요.

::: code-group

```sh [npm]
$ npm create granite-app
```

```sh [pnpm]
$ pnpm create granite-app
```

```sh [yarn]
$ yarn create granite-app
```

:::

### 1. 앱 이름 지정하기

앱 이름은 [kebab-case](https://developer.mozilla.org/en-US/docs/Glossary/Kebab_case) 형식으로 만들어 주세요.
예를 들어, 아래와 같이 입력해요.

```shell
# 예시
my-granite-app
```

### 2. 도구 선택하기

`granite`에서는 프로젝트를 생성할 때 필요한 도구를 선택할 수 있어요. 현재 제공되는 선택지는 다음 두 가지예요. 둘 중 한 가지 방법을 선택해서 개발 환경을 세팅하세요.

* `prettier` + `eslint`: 코드 포맷팅과 린팅을 각각 담당하며, 세밀한 설정과 다양한 플러그인으로 유연한 코드 품질 관리를 지원해요.
* `biome`: Rust 기반의 빠르고 통합적인 코드 포맷팅과 린팅 도구로, 간단한 설정으로 효율적인 작업이 가능해요.

### 3. 의존성 설치하기

프로젝트 디렉터리로 이동한 뒤, 사용 중인 패키지 관리자에 따라 의존성을 설치하세요.

::: code-group

```sh [npm]
$ cd my-granite-app
$ npm install
```

```sh [pnpm]
$ cd my-granite-app
$ pnpm install
```

```sh [yarn]
$ cd my-granite-app
$ yarn install
```

:::

### 스캐폴딩 전체 예시

아래는 `my-granite-app`이라는 이름으로 새로운 앱을 스캐폴딩한 결과예요.

스캐폴딩을 마쳤다면 프로젝트 구조가 생성돼요.

## 환경 구성하기

ReactNative SDK를 이용해 번들 파일을 생성하고 출시하는 방법을 소개해요.

### 설치하기

앱인토스 미니앱을 개발하려면 `@apps-in-toss/framework` 패키지를 설치해야 해요. 사용하는 패키지 매니저에 따라 아래 명령어를 실행하세요.

::: code-group

```sh [npm]
$ npm install @apps-in-toss/framework
```

```sh [pnpm]
$ pnpm install @apps-in-toss/framework
```

```sh [yarn]
$ yarn add @apps-in-toss/framework
```

:::

### 설정파일 구성하기

`ait init` 명령어로 앱 개발에 필요한 기본 환경을 구성할 수 있어요.

1. 아래 명령어 중 사용하는 패키지 관리자에 맞는 명령어를 실행하세요.\
   ::: code-group

   ```sh [npm]
    npx ait init
   ```

   ```sh [pnpm]
    pnpm ait init
   ```

   ```sh [yarn]
    yarn ait init
   ```

   :::

2. 프레임워크를 선택하세요.

3. 앱 이름(`appName`)을 입력하세요.

   이 이름은 앱인토스 콘솔에서 앱을 만들 때 사용한 이름과 같아야 해요. 앱인토스 콘솔에서 앱 이름을 확인할 수 있어요.

모든 과정을 완료하면 프로젝트 루트에 `granite.config.ts` 파일이 생성돼요. 이 파일은 앱 설정을 관리하는 데 사용돼요.

::: code-group

```ts [granite.config.ts]
import { appsInToss } from '@apps-in-toss/framework/plugins';
import { defineConfig } from '@granite-js/react-native/config';

export default defineConfig({
  appName: "<app-name>",
  plugins: [
    appsInToss({
      brand: {
        displayName: "%%appName%%", // 화면에 노출될 앱의 한글 이름으로 바꿔주세요.
        primaryColor: "#3182F6", // 화면에 노출될 앱의 기본 색상으로 바꿔주세요.
        icon: null, // 화면에 노출될 앱의 아이콘 이미지 주소로 바꿔주세요.
        bridgeColorMode: "basic",
      },
      permissions: [],
    }),
  ],
});
```

:::

* `<app-name>`: 앱인토스에서 만든 앱 이름이에요.
* `brand`: 앱 브랜드와 관련된 구성이에요.
  * `displayName`: 브릿지 뷰에 표시할 앱 이름이에요.
  * `icon`: 앱 아이콘 이미지 주소예요. 사용자에게 앱 브랜드를 전달해요.
  * `primaryColor`: Toss 디자인 시스템(TDS) 컴포넌트에서 사용할 대표 색상이에요. RGB HEX 형식(eg. `#3182F6`)으로 지정해요.
  * `bridgeColorMode`: 브릿지 뷰의 배경 색상 유형이에요. 흰 배경인 `basic` 또는 검은 배경인 `inverted` 중 하나를 선택할 수 있어요.
* `permissions`: [권한이 필요한 함수 앱 설정하기](/bedrock/reference/framework/권한/permission) 문서를 참고해서 설정하세요.

### TDS React Native 패키지 설치하기

`@apps-in-toss/framework`를 사용하려면 TDS React Native 패키지를 추가로 설치해야 해요. 자세한 내용은 [React Native TDS](https://tossmini-docs.toss.im/tds-react-native/)를 참고해 주세요.

### 번들 파일 생성하기

번들 파일은 `.ait` 확장자를 가진 파일로, 빌드된 프로젝트를 패키징한 결과물이에요. 이를 생성하려면 아래 명령어를 실행하세요.

::: code-group

```sh [npm]
npm run build
```

```sh [pnpm]
pnpm build
```

```sh [yarn]
yarn build
```

:::

위 명령어를 실행하면 프로젝트 루트 디렉터리에 `<서비스명>.ait` 파일이 생성돼요. 해당 파일은 앱을 출시할 때 사용해요.

### 앱 출시하기

앱을 출시하는 방법은 [앱 출시하기](/development/test/toss)문서를 참고하세요.

## 코드 확인해보기

프로젝트의 `_app.tsx` 파일에 다음과 같은 코드가 들어있을 거예요.

::: code-group

```tsx [_app.tsx]
import { AppsInToss } from '@apps-in-toss/framework';
import { PropsWithChildren } from 'react';
import { InitialProps } from '@granite-js/react-native';
import { context } from '../require.context';

function AppContainer({ children }: PropsWithChildren<InitialProps>) {
  return <>{children}</>;
}

export default AppsInToss.registerApp(AppContainer, { context });
```

:::

### 스캐폴딩 된 코드 알아보기

스캐폴딩 명령어를 실행하면 다음과 같은 파일이 생성돼요.

::: code-group

```tsx [/pages/index.tsx]
import { createRoute } from '@granite-js/react-native';
import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';

export const Route = createRoute('/', {
  component: Page,
});

function Page() {
  const navigation = Route.useNavigation();

  const goToAboutPage = () => {
    navigation.navigate('/about');
  };

  return (
    <Container>
      <Text style={styles.title}>🎉 Welcome! 🎉</Text>
      <Text style={styles.subtitle}>
        This is a demo page for the <Text style={styles.brandText}>Granite</Text> Framework.
      </Text>
      <Text style={styles.description}>This page was created to showcase the features of the Granite.</Text>
      <TouchableOpacity style={styles.button} onPress={goToAboutPage}>
        <Text style={styles.buttonText}>Go to About Page</Text>
      </TouchableOpacity>
    </Container>
  );
}

function Container({ children }: { children: React.ReactNode }) {
  return <View style={styles.container}>{children}</View>;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: 'white',
    justifyContent: 'center',
    alignItems: 'center',
  },
  brandText: {
    color: '#0064FF',
    fontWeight: 'bold',
  },
  text: {
    fontSize: 24,
    color: '#202632',
    textAlign: 'center',
    marginBottom: 10,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#1A202C',
    textAlign: 'center',
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 18,
    color: '#4A5568',
    textAlign: 'center',
    marginBottom: 24,
  },
  description: {
    fontSize: 16,
    color: '#718096',
    textAlign: 'center',
    marginBottom: 32,
    lineHeight: 24,
  },
  button: {
    backgroundColor: '#0064FF',
    paddingVertical: 12,
    paddingHorizontal: 32,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  codeContainer: {
    padding: 8,
    backgroundColor: '#333',
    borderRadius: 4,
    width: '100%',
  },
  code: {
    color: 'white',
    fontFamily: 'monospace',
    letterSpacing: 0.5,
    fontSize: 14,
  },
});

```

:::

## 파일 기반 라우팅 이해하기

Granite 개발 환경은 Next.js와 비슷한 [파일 시스템 기반의 라우팅](https://nextjs.org/docs/app/building-your-application/routing#roles-of-folders-and-files)을 사용해요.

파일 기반 라우팅은 파일 구조에 따라 자동으로 경로(URL 또는 스킴)가 결정되는 시스템이에요. 예를 들어, pages라는 디렉토리에 `detail.ts` 파일이 있다면, 이 파일은 자동으로 `/detail` 경로로 연결돼요.

Granite 애플리케이션에서는 이 개념이 스킴과 연결돼요. 스킴은 특정 화면으로 연결되는 주소인데요. 예를 들어, `pages/detail.ts`라는 파일은 자동으로 `intoss://my-granite-app/detail` 이라는 스킴으로 접근할 수 있는 화면이에요. 모든 Granite 화면은 `intoss://` 스킴으로 시작해요.

```
my-granite-app
└─ pages
    ├─ index.tsx       // intoss://my-granite-app
    ├─ detail.tsx      // intoss://my-granite-app/detail
    └─ item
        ├─ index.tsx    // intoss://my-granite-app/item
        └─ detail.tsx    // intoss://my-granite-app/item/detail
```

* `index.tsx` 파일: `intoss://my-granite-app`
* `detail.tsx` 파일: `intoss://my-granite-app/detail`
* `item/index.tsx` 파일: `intoss://my-granite-app/item`
* `item/detail.tsx` 파일: `intoss://my-granite-app/item/detail`

```jsx
┌─ 모든 Granite 화면을 가리키는 스킴은
│  intoss:// 으로 시작해요
│
-------------
intoss://my-granite-app/detail
         ==============~~~~~~~
             │           └─ pages 하위에 있는 경로를 나타내요
             │
             └─ 서비스 이름을 나타내요
```

이렇게 개발자는 별도로 라우팅 설정을 하지 않아도, 파일을 추가하기만 하면 새로운 화면이 자동으로 설정돼요.

## 서버 실행하기

### 로컬 개발 서버 실행하기

이제 여러분만의 Granite 페이지를 만들 준비가 끝났어요. 🎉
다음으로 로컬에서 `my-granite-app` 서비스를 실행해 볼게요.

::: info 앱 실행 환경을 먼저 설정하세요.

* [iOS 환경설정](/development/client/ios)
* [Android 환경설정](/development/client/android)

:::

스캐폴딩된 프로젝트 디렉터리로 이동한 뒤, 선택한 패키지 매니저를 사용해 `dev` 스크립트를 실행하세요. 이렇게 하면 개발 서버가 시작돼요.

::: code-group

```sh [npm]
$ cd my-granite-app
$ npm run dev
```

```sh [pnpm]
$ cd my-granite-app
$ pnpm dev
```

```sh [yarn]
$ cd my-granite-app
$ yarn dev
```

:::

명령어를 실행하면 아래와 같은 화면이 표시돼요.
![Metro 실행 예시](/assets/local-develop-js-1.B_LK2Zlw.png)

::: info 참고하세요
개발 서버 실행 중 too many open files 에러가 발생한다면, node\_modules 디렉터리를 삭제한 뒤 다시 의존성을 설치해 보세요.

```sh
rm -rf node_modules
npm install  # 또는 yarn, pnpm에 맞게
```

:::

::: info 실행 혹은 빌드시 '\[Apps In Toss Plugin] 플러그인 옵션이 올바르지 않습니다' 에러가 발생한다면?
'\[Apps In Toss Plugin] 플러그인 옵션이 올바르지 않습니다. granite.config.ts 구성을 확인해주세요.'\
라는 메시지가 보인다면, `granite.config.ts`의 `icon` 설정을 확인해주세요.\
아이콘을 아직 정하지 않았다면 ''(빈 문자열)로 비워둔 상태로도 테스트할 수 있어요.

```ts
...
displayName: 'test-app', // 화면에 노출될 앱의 한글 이름으로 바꿔주세요.
primaryColor: '#3182F6', // 화면에 노출될 앱의 기본 색상으로 바꿔주세요.
icon: '',// 화면에 노출될 앱의 아이콘 이미지 주소로 바꿔주세요.
...
```

:::

## 미니앱 실행하기(시뮬레이터·실기기)

:::info 준비가 필요해요
미니앱은 샌드박스 앱을 통해서만 실행되기때문에 **샌드박스 앱(테스트앱)** 설치가 필수입니다.\
개발 및 테스트를 위해 [샌드박스앱](/development/test/sandbox)을 설치해주세요.
:::

### iOS 시뮬레이터(샌드박스앱)에서 실행하기

1. **앱인토스 샌드박스 앱**을 실행해요.
2. 샌드박스 앱에서 스킴을 실행해요. 예를 들어 서비스 이름이 `kingtoss`라면, `intoss://kingtoss`를 입력하고 "스키마 열기" 버튼을 눌러주세요.
3. Metro 서버가 실행 중이라면 시뮬레이터와 자동으로 연결돼요. 화면 상단에 `Bundling {n}%...`가 표시되면 연결이 성공한 거예요.

아래는 iOS 시뮬레이터에서 로컬 서버를 연결한 후 "Welcome!" 페이지를 표시하는 예시예요.

### iOS 실기기에서 실행하기

### 서버 주소 입력하기

아이폰에서 **앱인토스 샌드박스 앱**을 실행하려면 로컬 서버와 같은 와이파이에 연결되어 있어야 해요. 아래 단계를 따라 설정하세요.

1. **샌드박스 앱**을 실행하면 **"로컬 네트워크" 권한 요청 메시지**가 표시돼요. 이때 **"허용"** 버튼을 눌러주세요.

2) **샌드박스 앱**에서 서버 주소를 입력하는 화면이 나타나요.

3) 컴퓨터에서 로컬 서버 IP 주소를 확인하고, 해당 주소를 입력한 뒤 저장해주세요.

   * IP 주소는 한 번 저장하면 앱을 다시 실행해도 변경되지 않아요.
   * macOS를 사용하는 경우, 터미널에서 `ipconfig getifaddr en0` 명령어로 로컬 서버의 IP 주소를 확인할 수 있어요.

4) **"스키마 열기"** 버튼을 눌러주세요.

5) 화면 상단에 `Bundling {n}%...` 텍스트가 표시되면 로컬 서버에 성공적으로 연결된 거예요.

::: details "로컬 네트워크"를 수동으로 허용하는 방법
**"로컬 네트워크" 권한을 허용하지 못한 경우, 아래 방법으로 수동 설정이 가능해요.**

1. 아이폰의 \[설정] 앱에서 **"앱인토스"** 를 검색해 이동해요.
2. **"로컬 네트워크"** 옵션을 찾아 켜주세요.

:::

***

### Android 실기기 또는 에뮬레이터 연결하기

1. Android 실기기(휴대폰 또는 태블릿)를 컴퓨터와 USB로 연결하세요. ([USB 연결 가이드](/development/client/android.html#기기-연결하기))

2. `adb` 명령어를 사용해서 `8081` 포트와 `5173`포트를 연결하고 연결 상태를 확인해요.

   **8081 포트, 5173 포트 연결하기**

   기기가 하나만 연결되어 있다면 아래 명령어만 실행해도 돼요.

   ```shell
   adb reverse tcp:8081 tcp:8081
   adb reverse tcp:5173 tcp:5173
   ```

   특정 기기를 연결하려면 `-s` 옵션과 디바이스 아이디를 추가해요.

   ```shell
   adb -s {디바이스아이디} reverse tcp:8081 tcp:8081
   # 예시: adb -s R3CX30039GZ reverse tcp:8081 tcp:8081
   adb -s {디바이스아이디} reverse tcp:5173 tcp:5173
   # 예시: adb -s R3CX30039GZ reverse tcp:5173 tcp:5173
   ```

   **연결 상태 확인하기**

   연결된 기기와 포트를 확인하려면 아래 명령어를 사용하세요.

   ```shell
   adb reverse --list
   # 연결된 경우 예시: UsbFfs tcp:8081 tcp:8081

   ```

   특정 기기를 확인하려면 `-s` 옵션을 추가해요.

   ```shell
   adb -s {디바이스아이디} reverse --list
   # 예시: adb -s R3CX30039GZ reverse --list

   # 연결된 경우 예시: UsbFfs tcp:8081 tcp:8081
   ```

3. **앱인토스 샌드박스 앱**에서 스킴을 실행하세요. 예를 들어, 서비스 이름이 `kingtoss`라면 `intoss://kingtoss`를 입력하고 실행 버튼을 누르세요.

4. Metro 서버가 실행 중이라면 실기기 또는 에뮬레이터와 자동으로 연결돼요. 화면 상단에 번들링 프로세스가 진행 중이면 연결이 완료된 거예요.

   아래는 Android 시뮬레이터에서 로컬 서버를 연결한 후 "Welcome!" 페이지를 표시하는 예시예요.

### 자주 쓰는 `adb` 명령어(Android)

개발 중에 자주 쓰는 `adb` 명령어를 정리했어요.

#### 연결 끊기

```shell
adb kill-server
```

#### 8081 포트 연결하기

```shell
adb reverse tcp:8081 tcp:8081
adb reverse tcp:5173 tcp:5173
# 특정 기기 연결: adb -s {디바이스아이디} reverse tcp:8081 tcp:8081
```

#### 연결 상태 확인하기

```shell
adb reverse --list
# 특정 기기 확인: adb -s {디바이스아이디} reverse --list
```

### 트러블슈팅

::: details Q. Metro 개발 서버가 열려 있는데 `잠시 문제가 생겼어요`라는 메시지가 표시돼요.

개발 서버에 제대로 연결되지 않은 문제일 수 있어요. `adb` 연결을 끊고 다시 `8081` 포트를 연결하세요.
:::

::: details Q. PC웹에서 Not Found 오류가 발생해요.

8081 포트는 샌드박스 내에서 인식하기 위한 포트예요.\
PC웹에서 8081 포트는 Not Found 오류가 발생해요.
:::

## 디버깅하기

### 1. 준비

React Native Debugger를 사용해서 JavaScript 디버깅을 하려면 Chrome 브라우저가 필요해요. 다음 링크로 브라우저를 다운로드 하세요.

* [Chrome 웹브라우저 다운로드 링크](https://www.google.com/intl/ko_kr/chrome/)

### 2. 개발 서버 실행

Metro 개발 서버는 React Native 애플리케이션을 개발할 때 코드 번들링, 핫 리로딩, 자원 제공 등의 역할을 해주는 번들러예요. 쉽게 말해서, 앱이 실행될 수 있도록 JavaScript 코드를 준비하고 관리하는 도구라고 생각하면 돼요.

다음 명령어로 Metro 개발 서버를 실행해서 디버깅을 시작해 볼게요.

```bash
yarn dev
# 또는
yarn granite dev
```

![Metro 개발 서버를 띄운 화면](/assets/debugging-1.z-bhdbHR.png)

### 3. 디버거 실행

개발 서버가 실행됐다면, 터미널에서 `j` 키를 눌러 React Native Debugger를 열 수 있어요. 다만, 아래와 같이 Metro와 테스트 기기 간의 연결이 이루어진 상태에서만 React Native Debugger가 열려요.

![기기와 연결된 상태](/assets/debugging-2.Uv7H5q5P.png)

***

### 탭 소개

Metro 개발 서버가 제공하는 디버깅 도구를 사용해서 편리하게 애플리케이션의 상태를 분석하고, 문제를 찾아 해결할 수 있어요. 각 탭에서는 모니터링하거나 조작할 수 있는 항목을 알아봐요.

![디버거 탭 소개 이미지](/assets/debugging-3.BmmXnth6.png)

* **Console**: [Console API](https://developer.mozilla.org/en-US/docs/Web/API/Console_API)를 통해 기록한 로그를 확인할 수 있어요. 또한, REPL(Read–Eval–Print Loop) 환경을 지원하기 때문에 코드를 입력하면 결과를 콘솔에서 확인할 수 있어요.

* **Source**: 현재 실행 중인 코드를 보고 중단점을 추가할 수 있어요.

* **Network**: 개발 서버에 연결된 서비스의 네트워크 활동을 확인할 수 있어요.

* **Memory**: Memory Snapshot을 기록해서 Hermes 엔진의 메모리 사용 상황을 프로파일링할 수 있어요.

* **Profiler**: 코드 실행 성능을 측정할 수 있는 도구예요.

***

### 기본 사용법

이제 Metro 개발 서버를 사용해서 React Native 애플리케이션에서 다양한 디버깅 기능을 활용하는 방법을 알아볼게요.

### 디버깅 공통

React Native 디버거를 사용하면 코드에서 발생하는 문제를 쉽게 찾고 해결할 수 있어요. 특히 유용한 기능은 Breakpoints에요. 이 기능을 사용하면 코드가 중단된 시점의 상태를 확인할 수 있어요. 가장 기본적인 기능은 다음과 같아요.

1. **Resume**: 일시 정지된 코드를 다시 실행해요.
2. **Scope 정보**: 현재 Scope에 접근 할 수 있는 변소와 그 값을 확인할 수 있어요.
3. **Call Stack**: 코드가 실행된 순서와 호출된 함수 목록, Call Stack을 확인할 수 있어요.

![Breakpoints 사용 예시 이미지 1](/assets/debugging-4.CGru5jtv.png)

일시정지된 시점에서 변수의 값을 바로 확인할 수도 있어요. 다음과 같이 변수 위로 마우스 커서를 올리면 돼요.

![Breakpoints 사용 예시 이미지 2](/assets/debugging-5.DMXIqUPk.png)

### debugger 키워드로 디버깅하기

또 다른 유용한 기능은 `debugger` 키워드예요. 이 키워드를 소스 코드에 추가하면 코드가 해당 지점에 도달했을 때 자동으로 중단되어 현재 상태를 살펴볼 수 있어요.

![debugger 코드 사용 예시 이미지](/assets/debugging-6.ClXobroT.png)

### 중단점으로 디버깅하기

중단점을 설정해서 특정 위치에서 코드 실행을 멈추는 기능도 사용할 수 있어요. 중단점을 추가하려면 커맨드(Command) + `P` 키를 눌러 파일 검색 창을 띄우고, 확인하고 싶은 파일명을 입력하세요.

![중단점 추가 예시 이미지 1](/assets/debugging-7.CZ1znzWG.png)

파일을 열었다면, 중단점을 설정하고 싶은 위치를 클릭해서 추가할 수 있어요. 중단점에 도달했을 때 코드 실행이 멈추면 현재 상태를 확인할 수 있어요.

![중단점 추가 예시 이미지 2](/assets/debugging-8.DtgBrLym.png)

### 예외 상황 디버깅하기

코드에서 예외(에러)가 발생했을 때 자동으로 그 지점에서 일시 정지되도록 설정할 수 있어요. 이 기능을 사용하면 미리 예상하지 못한 에러와 그 원인을 쉽게 파악할 수 있죠.

이 기능은 Metro 디버거의 **Source 탭**에서 설정할 수 있어요. 우측 상단의 Breakpoints 섹션에서 **"Pause on uncaught exceptions"** 을 활성화하면 예기치 못한 예외 발생 시 코드가 자동으로 중단돼요. **"Pause on caught exceptions"** 을 활성화하면 모든 예외(핸들링 여부와 관계없이)에서 일시 정지할 수 있어요.

![예외 상황 디버깅 설정 예시 이미지 1](/assets/debugging-9.ClKTRdaN.png)

![예외 상황 디버깅 설정 예시 이미지 2](/assets/debugging-10.CzJSb05R.png)

::: warning 유의하세요

서비스 코드에서 심각한 예외가 발생해 서비스가 완전히 중단된 후에 예외 Breakpoints가 제대로 동작하지 않는 버그가 있어요.

임시 해결 방법은 개발 서버와 React Native Debugger를 재시작하는 거예요.

:::

### 네트워크 활동 검사

React Native 애플리케이션의 네트워크 활동을 기록하고 확인할 수 있는 네트워크 인스펙터 기능을 사용해 볼게요.

네트워크 인스펙터를 사용하면 요청과 응답 데이터를 포함한 네트워크 활동을 다음과 같이 확인할 수 있어요. 이 도구를 사용하면 각 요청의 헤더와 응답 데이터를 상세히 분석할 수 있어요.

![네트워크 활동 검사 예시 이미지](/assets/debugging-11.B9rgsI54.png)

### 프로파일링

프로파일링 도구를 사용하면 React Native 애플리케이션의 메모리 사용량과 코드 실행 성능을 상세히 분석할 수 있어요. 이를 통해 성능 최적화와 메모리 누수 문제를 발견하고 해결할 수 있죠.

### 메모리

메모리 프로파일링 기능은 메모리 사용량을 분석하고, 메모리 누수를 탐지하는 데 유용해요. 이 도구를 사용해 앱이 메모리를 어떻게 관리하고 있는지 확인할 수 있어요.

1. 먼저, 프로파일링 유형을 선택하세요.
2. **"Take snapshot"** 버튼을 눌러 스냅샷을 기록할 수 있어요.
3. 기록된 스냅샷을 보며 메모리 사용 상태를 분석하고 필요한 정보를 찾아요.

![메모리 프로파일링 예시 이미지 1](/assets/debugging-13.jnuQ2VYs.png)

![메모리 프로파일링 예시 이미지 2](/assets/debugging-14.B2iOWS_g.png)

### 성능 측정

성능 측정 도구를 사용하면 코드의 실행 성능을 분석할 수 있어요. 이 기능은 성능 최적화가 필요한 부분을 식별하고 개선하는 데 유용해요.

다음은 성능 측정 도구의 사용 예시에요. 이 도구를 사용해 기록을 시작하고, 실행된 코드의 성능을 평가할 수 있어요.

![성능 측정 도구 사용 예시 1](/assets/debugging-15.BWSJK_qd.png)

![성능 측정 도구 사용 예시 2](/assets/debugging-16.Bir56t9S.png)

### React DevTools로 디버깅하기

React DevTools는 React Native 애플리케이션의 컴포넌트 구조를 시각적으로 탐색하고 디버깅할 수 있는 도구예요. 디버깅 도구의 React DevTools에서 바로 사용할 수 있어요.

### 기기와 연결하기

React DevTools를 사용하려면 먼저 개발 중인 애플리케이션의 연결이 필요해요.

서비스가 실행되기 전이라면 개발 모드에서 React Native 서비스를 실행해 주세요. 서비스가 이미 실행 중이라면, 개발 모드 RN 뷰를 **새로고침**해야 해요. `R` 키를 눌러서 새로고침해주세요.

![React DevTools 기기와 연결하기 1](/assets/debugging-17.Cp8ggGjb.png)

다음과 같이 React DevTools 화면이 나타나면 연결이 완료된 거예요.

![React DevTools 기기와 연결하기 2](/assets/debugging-18.LatrvStk.png)

안드로이드 기기를 사용한다면, `adb reverse tcp:8097 tcp:8097` 명령어를 입력해서 포트를 열어야 React DevTools가 정상적으로 동작해요. 만약 문제가 있다면 담당자에게 문의해주세요.

### 사용 팁

React DevTools에 있는 여러 유용한 기능을 효과적으로 사용하는 몇 가지 팁을 알려드릴게요.

#### 요소 인스펙팅

특정 요소를 쉽게 찾고 확인할 수 있는 기능이에요. 요소 선택 버튼을 누른 뒤, 테스트 중인 기기에서 확인할 요소를 터치하면 React DevTools에서 해당 요소로 바로 이동해요.

![인스펙팅 화면](/assets/debugging-19.C2F2iBKp.png)

#### Prop 변경하기

선택한 컴포넌트의 Prop(속성)을 확인하고, 실시간으로 변경할 수 있어요. 원하는 Prop을 더블 클릭한 뒤 값을 입력하면 바로 반영됩니다.

![Prop 변경 사용 예시 이미지](/assets/debugging-20.DZ4Jcbyg.png)

#### Suspense 테스트하기

Suspense 요소의 대기 상태를 시뮬레이션할 수 있는 기능이에요. 타이머 아이콘을 눌러 Suspense 대기 상태를 테스트해볼 수 있어요.

![Suspense 테스트 사용 예시 이미지](/assets/debugging-21.aDDmsPh8.png)

#### 상세 정보 로깅하기

특정 요소의 세부 정보를 콘솔에서 확인할 수 있어요. 디버그 버튼을 누르면 선택한 요소의 세부 정보가 콘솔에 기록됩니다.

![상세 정보 로깅 예시 이미지](/assets/debugging-22.B1aIn4qo.png)

## 토스앱에서 테스트하기

토스앱에서 테스트하는 방법은 [토스앱](/development/test/toss) 문서를 참고하세요.

## 출시하기

출시하는 방법은 [미니앱 출시](/development/deploy) 문서를 참고하세요.

## 트러블슈팅

::: details 연결 가능한 기기가 없다고 떠요

React Native View가 나타나는 시점에 개발 서버와 기기가 연결됩니다. 만약 연결 가능한 기기가 없다고 뜬다면, 개발 서버가 제대로 빌드되고 있는지 확인해 보세요. 다음 화면처럼 개발 서버가 빌드를 시작했다면 기기와의 연결이 정상적으로 이루어진 것입니다.

![개발 서버 연결 상태 확인 이미지](/assets/debugging-22.B1aIn4qo.png)
:::

::: details REPL가 동작하지 않아요

React Native의 버그로 인해 가끔 REPL이 멈추는 현상이 발생할 수 있어요. 이 문제를 해결하려면, 콘솔 탭 옆에 있는 눈 모양 아이콘을 클릭하고 입력 필드에 임의의 코드를 작성하고 평가해 보세요. 예를 들어 `__DEV__`, `1`, `undefined` 등의 코드를 입력하면 돼요.

![REPL 프리징 해결 방법 이미지](/resources/learn-more/debugging/debugging-23.png)

:::

::: details 네트워크 인스펙터가 동작하지 않아요

React Native 애플리케이션에서 여러 개의 인스턴스가 생성될 수 있는데, 현재 네트워크 인스펙터는 다중 인스턴스를 지원하지 않아요. 따라서 가장 최근에 생성된 인스턴스와만 데이터를 주고받게 됩니다. 이로 인해 소켓 커넥션이 꼬여 네이티브에서 전송하는 데이터를 인스펙터가 받지 못할 수 있어요.

이 문제를 해결하려면 다음을 시도해 보세요.

1. 앱을 완전히 종료해요.
2. 개발 서버를 중단하고 네트워크 인스펙터를 닫아요.
3. 앱을 다시 시작하고 `dev` 스크립트를 실행해 개발 서버를 재실행해요.

이 절차로도 문제가 해결되지 않으면, 담당자에게 제보해 주세요.

:::

기타 다른 문제가 발생했다면, 다음을 시도해 보세요.

1. 앱을 완전히 종료해요.
2. 개발 서버를 중단하고 네트워크 인스펙터를 닫아요.
3. 앱을 다시 시작하고 `dev` 스크립트를 실행해 개발 서버를 재실행해요.

이 절차로도 문제가 해결되지 않으면, 담당자에게 제보해 주세요.
