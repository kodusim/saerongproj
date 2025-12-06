---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/분석/LoggingArea.md
---

# 영역 단위로 기록하기

## `LoggingArea`

`LoggingArea` 함수로 여러 컴포넌트의 텍스트를 하나로 묶어서 로그를 남길 수 있어요. 지정한 영역이 노출되거나 클릭 했을 때 로그를 수집할 수 있어요.

## 시그니처

```typescript
function LoggingArea({ children, params: _params, ...props }: LoggingAreaProps): import("react/jsx-runtime").JSX.Element;
```

## 예제

### 여러 컴포넌트를 하나의 영역으로 묶어서 분석하는 예시

```tsx
import { Analytics } from '@apps-in-toss/framework';
import { View, Text } from 'react-native';

// 영역 안의 노출이나 클릭 정보를 자동으로 수집해요.
function TrackElements() {
  return (
    <Analytics.Area>
      <View>
        <Text>Hello</Text>
        <Text>World!</Text>
      </View>
    </Analytics.Area>
  );
}
```
