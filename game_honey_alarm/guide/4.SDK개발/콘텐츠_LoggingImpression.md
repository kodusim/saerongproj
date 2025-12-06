---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/분석/LoggingImpression.md
---

# 컴포넌트 노출 기록하기

## `LoggingImpression`

`LoggingImpression` 는 요소가 뷰포트에 표시되었는지 판단하고 로그를 남기는 컴포넌트예요. 예를 들어, 스크롤 아래에 있는 요소가 뷰포트에 표시되었을 때를 감지해 로그를 남겨요.

## 시그니처

```typescript
function LoggingImpression({ enabled, impression: impressionType, ...props }: LoggingImpressionProps): import("react/jsx-runtime").JSX.Element;
```

## 예제

### 컴포넌트의 노출 정보를 자동으로 수집하는 예시

```tsx
import { Analytics } from '@apps-in-toss/framework';

// 영역 안의 노출 정보를 자동으로 수집해요.
function TrackElements() {
  return (
    <Analytics.Impression>
      <Text>Hello</Text>
    </Analytics.Impression>
  );
}
```
