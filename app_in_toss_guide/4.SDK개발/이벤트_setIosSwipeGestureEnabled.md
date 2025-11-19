---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/setIosSwipeGestureEnabled.md
---

# iOS 스와이프 설정하기

## `setIosSwipeGestureEnabled`

`setIosSwipeGestureEnabled` 함수는 iOS에서 화면을 스와이프하여 뒤로가기 기능을 활성화하거나 비활성화할 수 있어요.

## 시그니처

```typescript
function setIosSwipeGestureEnabled(options: {
    isEnabled: boolean;
}): Promise<void>;
```

### 파라미터

### 반환 값

## 예제

### iOS에서 화면 스와이프로 뒤로가기 기능을 활성화하거나 비활성화하기

**스와이프 끄기** 버튼을 눌러 화면 스와이프로 뒤로가기 기능을 비활성화하거나, **스와이프 켜기** 버튼을 눌러 화면 스와이프로 뒤로가기 기능을 활성화할 수 있어요.

```tsx
import { setIosSwipeGestureEnabled } from '@apps-in-toss/framework';
import { Button } from 'react-native';

function Page() {
 return (
   <>
    <Button title="스와이프 끄기" onPress={() => setIosSwipeGestureEnabled({ isEnabled: false })} />
    <Button title="스와이프 켜기" onPress={() => setIosSwipeGestureEnabled({ isEnabled: true })} />
   </>
 );
}
```
