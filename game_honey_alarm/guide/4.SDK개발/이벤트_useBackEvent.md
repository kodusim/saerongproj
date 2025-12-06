---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/useBackEvent.md
---

# 뒤로가기 이벤트 제어하기

## `useBackEvent`

`useBackEvent` 는 뒤로 가기 이벤트를 등록하고 제거할 수 있는 컨트롤러 객체를 반환하는 Hook이에요. 이 Hook을 사용하면 특정 컴포넌트가 활성화되었을 때만 뒤로 가기 이벤트를 처리할 수 있어요.
`addEventListener` 를 쓰면 뒤로 가기 이벤트를 등록할 수 있고, `removeEventListener` 를 쓰면 뒤로 가기 이벤트를 제거할 수 있어요.
사용자가 화면을 보고 있을 때만 등록된 뒤로 가기 이벤트가 등록돼요. 화면을 보고 있다는 조건은 [useVisibility](/bedrock/reference/framework/화면%20제어/useVisibility.md) 을 사용해요.

이 Hook을 사용해 특정 컴포넌트에서 뒤로 가기 이벤트를 처리하는 로직을 정의할 수 있어요.

## 시그니처

```typescript
function useBackEvent(): BackEventControls;
```

### 반환 값

### 에러

## 예제

### 뒤로 가기 이벤트 등록 및 제거 예제

* **"Add BackEvent" 버튼을 누르면 뒤로 가기 이벤트가 등록돼요.** 이후 뒤로 가기 버튼을 누르면 "back"이라는 알림이 뜨고, 실제로 뒤로 가지 않아요.
* **"Remove BackEvent" 버튼을 누르면 등록된 이벤트가 제거돼요.** 이후 뒤로 가기 버튼을 누르면 기존 동작대로 정상적으로 뒤로 가요.

```tsx
import { useEffect, useState } from "react";
import { Alert, Button, View } from "react-native";
import { useBackEvent } from '@granite-js/react-native';

function UseBackEventExample() {
  const backEvent = useBackEvent();

  const [handler, setHandler] = useState<{ callback: () => void } | undefined>(
    undefined
  );

  useEffect(() => {
    const callback = handler?.callback;

    if (callback != null) {
      backEvent.addEventListener(callback);

      return () => {
        backEvent.removeEventListener(callback);
      };
    }

    return;
  }, [backEvent, handler]);

  return (
    <View>
      <Button
        title="Add BackEvent"
        onPress={() => {
          setHandler({ callback: () => Alert.alert("back") });
        }}
      />
      <Button
        title="Remove BackEvent"
        onPress={() => {
          setHandler(undefined);
        }}
      />
    </View>
  );
}
```
