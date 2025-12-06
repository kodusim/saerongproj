---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/setDeviceOrientation.md
---

# 화면 방향 설정하기

## `setDeviceOrientation`

`setDeviceOrientation` 함수는 기기의 화면 방향을 설정하는 기능을 제공해요.
이 기능은 특정 화면에서 가로 모드나 세로 모드를 강제로 지정해야 할 때 유용해요.

`type` 옵션을 통해 원하는 화면 방향을 지정할 수 있어요. 특히, 이 함수는 앱 전체에 영향을 미치므로
특정 화면에서만 사용하려면 화면을 벗어날 때 이전 상태로 복구하는 추가 작업이 필요해요.

예를 들어, 동영상 감상 화면에서는 가로 모드를 강제하고, 화면을 떠날 때 설정을 복구해서
다른 화면들의 방향 설정에 영향을 주지 않도록 할 수 있어요.

## 시그니처

```typescript
function setDeviceOrientation(options: {
  type: 'portrait' | 'landscape';
}): Promise<void>;
```

### 파라미터

'portrait' | 'landscape' 중 하나를 선택할 수 있어요.

### 반환 값

## 예제

### 화면 방향 설정하기

::: code-group

```tsx [React]
import { setDeviceOrientation } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';

function SetDeviceOrientationButton() {
  function handleClick() {
    setDeviceOrientation({ type: 'landscape' });
  }

  return <Button onClick={handleClick}>가로 모드로 변경</Button>;
}
```

```tsx [React Native]
import { setDeviceOrientation } from '@apps-in-toss/framework';
import { Button } from '@toss/tds-react-native';

function SetDeviceOrientationButton() {
  function handlePress() {
    setDeviceOrientation({ type: 'landscape' });
  }

  return <Button onPress={handlePress}>가로 모드로 변경</Button>;
}
```

:::

### 화면 방향 복구하기

특정 화면을 벗어날 때 이전 상태로 복구하려면 다음과 같이 `useEffect`를 사용하세요.

::: code-group

```tsx [React]
import { setDeviceOrientation } from '@apps-in-toss/web-framework';
import { Text } from '@toss/tds-mobile';
import { useEffect } from 'react';

function VideoScreen() {
  useEffect(() => {
    setDeviceOrientation({ type: 'landscape' });

    return () => {
      setDeviceOrientation({ type: 'portrait' }); // 설정을 이전 상태로 복구해요.
    };
  }, []);

  return <Text>동영상을 감상하는 화면</Text>;
}
```

```tsx [React Native]
import { setDeviceOrientation } from '@apps-in-toss/framework';
import { Text } from '@toss/tds-react-native';
import { useEffect } from 'react';

function VideoScreen() {
  useEffect(() => {
    setDeviceOrientation({ type: 'landscape' });

    return () => {
      setDeviceOrientation({ type: 'portrait' }); // 설정을 이전 상태로 복구해요.
    };
  }, []);

  return <Text>동영상을 감상하는 화면</Text>;
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-game](https://github.com/toss/apps-in-toss-examples/tree/main/with-game) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
