---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/클립보드/getClipboardText.md
---

# 클립보드 텍스트 가져오기

## `getClipboardText`

클립보드에 저장된 텍스트를 가져오는 함수예요. 복사된 텍스트를 읽어서 다른 작업에 활용할 수 있어요.

## 시그니처

```typescript
function getClipboardText(): Promise<string>;
```

### 프로퍼티

### 반환 값

## GetClipboardTextPermissionError

클립보드 읽기 권한이 거부되었을 때 발생하는 에러예요. 에러가 발생했을 때 `error instanceof GetClipboardTextPermissionError`를 통해 확인할 수 있어요.

## 시그니처

```typescript
class GetClipboardTextPermissionError extends PermissionError {
    constructor();
}
```

## 예제

### 클립보드의 텍스트 가져오기

클립보드의 텍스트를 가져오는 예제예요.
"권한 확인하기"버튼을 눌러서 현재 클립보드 읽기 권한을 확인해요.
사용자가 권한을 거부했거나 시스템에서 권한이 제한된 경우에는 [`GetClipboardTextPermissionError`](./GetClipboardTextPermissionError)를 반환해요.
"권한 요청하기"버튼을 눌러서 클립보드 읽기 권한을 요청할 수 있어요.

::: code-group

```tsx [React]
import {
  getClipboardText,
  GetClipboardTextPermissionError,
  SetClipboardTextPermissionError,
} from '@apps-in-toss/web-framework';
import { useState } from 'react';
 *

// '붙여넣기' 버튼을 누르면 클립보드에 저장된 텍스트를 가져와 화면에 표시해요.
function PasteButton() {
  const [text, setText] = useState(''); 

  const handlePress = async () => {
    try {
      const clipboardText = await getClipboardText();
      setText(clipboardText || '클립보드에 텍스트가 없어요.');
    } catch (error) {
      if (error instanceof GetClipboardTextPermissionError) {
        // 클립보드 읽기 권한 없음
      } 

      if (error instanceof SetClipboardTextPermissionError) {
        // 클립보드 쓰기 권한 없음
      }
    }
  };

  return (
    <div>
      <span>{text}</span>
      <input type="button" value="붙여넣기" onClick={handlePress} />
      <input type="button"
        value="권한 확인하기"
        onClick={async () => {
          const permission = await getClipboardText.getPermission();
          alert(permission);
        }}
      />
      <input type="button"
        value="권한 요청하기"
        onClick={async () => {
          const permission = await getClipboardText.openPermissionDialog();
          alert(permission);
        }}
      />
    </div>
  );
}
```

```tsx [React Native]
import {
  getClipboardText,
  GetClipboardTextPermissionError,
  SetClipboardTextPermissionError,
} from '@apps-in-toss/framework';
import { useState } from 'react';
import { Alert, Button, Text, View } from 'react-native';

// '붙여넣기' 버튼을 누르면 클립보드에 저장된 텍스트를 가져와 화면에 표시해요.
function PasteButton() {
  const [text, setText] = useState('');

  const handlePress = async () => {
    try {
      const clipboardText = await getClipboardText();
      setText(clipboardText || '클립보드에 텍스트가 없어요.');
    } catch (error) {
      if (error instanceof GetClipboardTextPermissionError) {
        // 클립보드 읽기 권한 없음
      }

      if (error instanceof SetClipboardTextPermissionError) {
        // 클립보드 쓰기 권한 없음
      }
    }
  };

  return (
    <View>
      <Text>{text}</Text>
      <Button title="붙여넣기" onPress={handlePress} />
      <Button
        title="권한 확인하기"
        onPress={async () => {
          const permission = await getClipboardText.getPermission();
          Alert.alert(permission);
        }}
      />
      <Button
        title="권한 요청하기"
        onPress={async () => {
          const permission = await getClipboardText.openPermissionDialog();
          Alert.alert(permission);
        }}
      />
    </View>
  );
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-clipboard-text](https://github.com/toss/apps-in-toss-examples/tree/main/with-clipboard-text) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
