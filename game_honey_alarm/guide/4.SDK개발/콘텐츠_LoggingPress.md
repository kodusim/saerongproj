---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/분석/LoggingPress.md
---

# 클릭 이벤트 기록하기

## `LoggingPress`

`LoggingPress` 는 요소가 사용자 액션에 의해 눌렸을 때 눌렸다고 로그를 남기는 컴포넌트예요. 예를 들어, 버튼을 눌러 구매를 하는 로그를 남기고 싶을 때 사용해요.

::: info 잠시만요

샌드박스나 QR 테스트 환경에서는 클릭 이벤트가 실제로 쌓이지 않아요.

이벤트는 라이브 환경에서만 수집돼요.

또한 콘솔에서 데이터를 확인할 수 있는 시점은 **+1일 후** 예요.

:::

## 시그니처

```typescript
LoggingPress: import("react").ForwardRefExoticComponent<LoggingPressProps & import("react").RefAttributes<unknown>>
```

## 예제

### 클릭 가능한 요소의 클릭 이벤트를 자동으로 수집하는 예시

```tsx
import { Analytics } from '@apps-in-toss/framework';
import { Button } from 'react-native';

// 클릭 가능한 요소의 클릭 이벤트를 자동으로 수집해요.
function TrackElements() {
  return (
    <Analytics.Press>
      <Button label="Press Me" />
    </Analytics.Press>
  );
}
```
