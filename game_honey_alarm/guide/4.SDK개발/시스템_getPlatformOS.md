---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/환경
  확인/getPlatformOS.md
---

# 실행중인 플랫폼 확인하기

## `getPlatformOS`

`getPlatformOS` 는 현재 실행 중인 플랫폼을 확인하는 함수예요.
이 함수는 `react-native`의 [`Platform.OS`](https://reactnative.dev/docs/0.72/platform#os) 값을 기반으로 동작하며, `ios` 또는 `android` 중 하나의 문자열을 반환해요.

## 시그니처

```typescript
function getPlatformOS(): 'ios' | 'android';
```

### 반환 값

## 예제

### 현재 실행중인 OS 플랫폼 확인하기

```tsx
import { getPlatformOS } from '@apps-in-toss/framework';
import { Text } 'react-native';

function Page() {
  const platform = getPlatformOS();

  return <Text>현재 플랫폼: {platform}</Text>;
}
```
