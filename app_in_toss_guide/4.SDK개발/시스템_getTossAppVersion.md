---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/환경
  확인/getTossAppVersion.md
---

# 토스앱 버전 가져오기

## `getTossAppVersion`

`getTossAppVersion` 함수는 토스 앱 버전을 가져옵니다. 예를 들어, `5.206.0`과 같은 형태로 반환돼요. 토스 앱 버전을 로그로 남기거나, 특정 기능이 특정 버전 이상에서만 실행될 때 사용돼요.

## 시그니처

```typescript
function getTossAppVersion(): string
```

### 반환 값

## 예제

### 토스 앱 버전 확인하기

::: code-group

```tsx [React]
import { getTossAppVersion } from '@apps-in-toss/web-framework';
import { Text } from '@toss/tds-mobile';

function TossAppVersionPage() {
  const tossAppVersion = getTossAppVersion();

  return <Text>{tossAppVersion}</Text>;
}
```

```tsx [React Native]
import { getTossAppVersion } from '@apps-in-toss/framework';
import { Text } from '@toss/tds-react-native';

function TossAppVersionPage() {
  const tossAppVersion = getTossAppVersion();

  return <Text>{tossAppVersion}</Text>;
}
```

:::
