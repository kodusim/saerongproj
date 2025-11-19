---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/인터렉션/generateHapticFeedback.md
---

# 햅틱 진동 실행하기

## `generateHapticFeedback`

`generateHapticFeedback`은 디바이스에서 햅틱 진동을 발생시키는 함수예요.\
버튼 터치나 화면 전환 시, 촉각적인 반응을 주고 싶을 때 사용할 수 있어요.

### 시그니처

```typescript
function generateHapticFeedback(options: HapticFeedbackOptions): Promise<void>;
```

### 반환 값

### 예제 : 버튼을 눌러 햅틱 일으키기

::: code-group

```tsx [React]
import React from "react";
import { generateHapticFeedback } from "@apps-in-toss/web-framework";

function GenerateHapticFeedbackWeb() {
  return (
    <button
      onClick={() => {
        generateHapticFeedback({ type: "tickWeak" });
      }}
      style={{
        padding: "10px 20px",
        borderRadius: "8px",
        border: "none",
        backgroundColor: "#3182f6",
        color: "white",
        cursor: "pointer",
        fontSize: "16px",
      }}
    >
      햅틱
    </button>
  );
}

export default GenerateHapticFeedbackWeb;
```

```tsx [React Native]
import { Button } from "react-native";
import { generateHapticFeedback } from '@apps-in-toss/framework';

function GenerateHapticFeedback() {
  return (
    <Button
      title="햅틱"
      onPress={() => {
        generateHapticFeedback({ type: "tickWeak" });
      }}
    />
  );
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-haptic-feedback](https://github.com/toss/apps-in-toss-examples/tree/main/with-haptic-feedback) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.

## `HapticFeedbackOptions`

`HapticFeedbackOptions`는 `generateHapticFeedback` 함수에 전달할 진동의 타입을 정의해요.\
사용 가능한 진동 타입은 아래와 같습니다.

```typescript
type HapticFeedbackType =
| "tickWeak"
| "tap"
| "tickMedium"
| "softMedium"
| "basicWeak"
| "basicMedium"
| "success"
| "error"
| "wiggle"
| "confetti";
```

### 시그니처

```typescript
interface HapticFeedbackOptions {
    type: HapticFeedbackType;
}
```

### 타입 정의

#### `HapticFeedbackOptions`

*`type: HapticFeedbackType`*

#### `HapticFeedbackType`

*`"tickWeak" | "tap" | "tickMedium" | "softMedium" | "basicWeak" | "basicMedium" | "success" | "error" | "wiggle" | "confetti"`*
