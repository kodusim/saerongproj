---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/closeView.md
---

# 화면 닫기

## `closeView`

`closeView` 는 현재 화면을 닫는 함수에요. 예를 들어, "닫기" 버튼을 눌러서 서비스를 종료할 때 사용할 수 있어요.

## 시그니처

```typescript
function closeView(): Promise<void>;
```

### 반환 값

## 예제

### 닫기 버튼을 눌러 화면 닫기

```tsx
import { Button } from 'react-native';
import { closeView } from '@granite-js/react-native';

function CloseButton() {
 return <Button title="닫기" onPress={closeView} />;
}
```
