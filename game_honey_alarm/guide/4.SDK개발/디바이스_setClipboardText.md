---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/클립보드/setClipboardText.md
---

# 클립보드 텍스트 복사하기

## `setClipboardText`

텍스트를 클립보드에 복사해서 사용자가 다른 곳에 붙여 넣기 할 수 있어요.

## 시그니처

```typescript
function setClipboardText(text: string): Promise<void>;
```

### 파라미터

### 프로퍼티

## SetClipboardTextPermissionError

클립보드 쓰기 권한이 거부되었을 때 발생하는 에러예요. 에러가 발생했을 때 `error instanceof SetClipboardTextPermissionError`를 통해 확인할 수 있어요.

## 시그니처

```typescript
class SetClipboardTextPermissionError extends PermissionError {
    constructor();
}
```

## 예제

### 텍스트를 클립보드에 복사하기

텍스트를 클립보드에 복사하는 예제예요.
"권한 확인하기"버튼을 눌러서 현재 클립보드 쓰기 권한을 확인해요.
사용자가 권한을 거부했거나 시스템에서 권한이 제한된 경우에는 [`SetClipboardTextPermissionError`](./SetClipboardTextPermissionError)를 반환해요.
"권한 요청하기"버튼을 눌러서 클립보드 쓰기 권한을 요청할 수 있어요.

::: code-group

```tsx [React]
import { setClipboardText, SetClipboardTextPermissionError } from '@apps-in-toss/web-framework';


// '복사' 버튼을 누르면 "복사할 텍스트"가 클립보드에 복사돼요.
function CopyButton() {
  const handleCopy = async () => {
    try {
      await setClipboardText('복사할 텍스트');
      console.log('텍스트가 복사됐어요!');
    } catch (error) {
      if (error instanceof SetClipboardTextPermissionError) {
        // 텍스트 쓰기 권한 거부됨
      }
    }
  };

  return (
    <>
      <input type="button" value="복사" onClick={handleCopy} />
      <input type="button"
        value="권한 확인하기"
        onClick={async () => {
          const permission = await setClipboardText.getPermission();
          Alert.alert(permission);
        }}
      />
      <input type="button"
        value="권한 요청하기"
        onClick={async () => {
          const permission = await setClipboardText.openPermissionDialog();
          Alert.alert(permission);
        }}
      />
    </>
  );
}
```

```tsx [React Native]
import { setClipboardText, SetClipboardTextPermissionError } from '@apps-in-toss/framework';
import { Alert, Button } from 'react-native';

// '복사' 버튼을 누르면 "복사할 텍스트"가 클립보드에 복사돼요.
function CopyButton() {
  const handleCopy = async () => {
    try {
      await setClipboardText('복사할 텍스트');
      console.log('텍스트가 복사됐어요!');
    } catch (error) {
      if (error instanceof SetClipboardTextPermissionError) {
        // 텍스트 쓰기 권한 거부됨
      }
    }
  };

  return (
    <>
      <Button title="복사" onPress={handleCopy} />
      <Button
        title="권한 확인하기"
        onPress={async () => {
          const permission = await setClipboardText.getPermission();
          Alert.alert(permission);
        }}
      />
      <Button
        title="권한 요청하기"
        onPress={async () => {
          const permission = await setClipboardText.openPermissionDialog();
          Alert.alert(permission);
        }}
      />
    </>
  );
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-clipboard-text](https://github.com/toss/apps-in-toss-examples/tree/main/with-clipboard-text) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
