---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  이동/openURL.md
---

# 외부 URL 열기

## `openURL`

`openURL` 함수는 지정된 URL을 기기의 기본 브라우저나 관련 앱에서 열어요.
이 함수는 `react-native`의 [`Linking.openURL`](https://reactnative.dev/docs/0.72/linking#openurl) 메서드를 사용하여 URL을 열어요.

## 시그니처

```typescript
function openURL(url: string): Promise<any>;
```

### 파라미터

### 반환 값

## 예제

### 외부 URL 열기

```tsx
import { openURL } from '@granite-js/react-native';
import { Button } from 'react-native';

function Page() {
  const handlePress = () => {
    openURL('https://google.com');
  };

  return <Button title="구글 웹사이트 열기" onPress={handlePress} />;
}
```
