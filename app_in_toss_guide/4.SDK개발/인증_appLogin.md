---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/로그인/appLogin.md
---

# 토스 인증 로그인

## `appLogin`

`appLogin` 함수는 토스 인증으로 로그인해요. 로그인이 완료되면 다시 토스 앱으로 이동해요.

## 시그니처

```typescript
function appLogin(): Promise<{
  authorizationCode: string;
  referrer: "DEFAULT" | "SANDBOX";
}>;
```

## 예제

### 토스 인증을 통해 로그인을 하는 예제

::: code-group

```tsx [React]
import { appLogin } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';

function Page() {
  async function handleLogin() {
    const { authorizationCode, referrer } = await appLogin();

    // 획득한 인가 코드(`authorizationCode`)와 `referrer`를 서버로 전달해요.
  }

  return <Button size="medium" onClick={handleLogin}>로그인</Button>;
}
```

```tsx [React Native]
import { appLogin } from '@apps-in-toss/framework';
import { Button } from "@toss/tds-react-native";

function Page() {
  async function handleLogin() {
    const { authorizationCode, referrer } = await appLogin();

    // 획득한 인가 코드(`authorizationCode`)와 `referrer`를 서버로 전달해요.
  }

  return <Button onPress={handleLogin}>로그인</Button>;
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-app-login](https://github.com/toss/apps-in-toss-examples/tree/main/with-app-login) 코드를 내려받아 체험해 보세요.
