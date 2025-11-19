---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/이벤트
  제어/back-event.md
---

# 뒤로가기 버튼 이벤트 제어하기

## `graniteEvent`

`graniteEvent`를 사용하면 네이티브 앱에서 웹 앱으로 전달되는 이벤트를 감지할 수 있어요. 이 중 `backEvent`는 뒤로가기 버튼을 눌렀을 때 웹 앱으로 전달되는 이벤트예요.  React Native는 `useBackEvent` 를 쓸 수 있어요.

## 해결하는 문제

* 사용자가 **중요한 작업 도중 실수로 뒤로가기 버튼을 눌러 화면이 닫히는 상황을 방지**할 수 있어요.
* 예를 들어, 결제 중이거나 폼을 작성 중일 때 뒤로가기를 막고 싶을 때 사용해요.
* `backEvent`를 감지해서 사용자에게 확인창을 보여주고, 확인한 경우에만 이동을 허용할 수 있어요.

## 동작 방식

`graniteEvent.addEventListener('backEvent', options)`로 이벤트를 구독할 수 있어요.

* `onEvent`: 사용자가 뒤로가기 버튼을 눌렀을 때 호출돼요. 아무 작업도 하지 않으면 기본 동작이 차단돼요.
* `onError`: 이벤트 처리 중 에러가 발생하면 호출돼요. 사용자에게 알림을 보여주거나, 오류 로그를 남길 수 있어요.

이벤트 리스너는 함수에서 반환된 `unsubscription()` 함수를 호출하면 해제할 수 있어요.

## 사용 예시

사용자가 뒤로가기 버튼을 눌렀을 때 확인창을 띄우고, '확인'을 누르면 이동을 허용해요. '취소'를 누르면 현재 화면에 머물러요.
::: code-group

```tsx [React]
import { graniteEvent } from '@apps-in-toss/web-framework';
import { useEffect, useState } from 'react';

/**
 * 작성 중인 내용을 보호하기 위해 뒤로가기를 차단하고,
 * 사용자의 확인을 받은 경우에만 허용하는 컴포넌트예요.
 * 
 * @example
 * import { ConfirmBackNavigation } from './ConfirmBackNavigation';
 * 
 * const App = () => <ConfirmBackNavigation />;
 */
function ConfirmBackNavigation() {
  const [formValue, setFormValue] = useState('');

  useEffect(() => {
    // 뒤로가기 버튼 눌렀을 때 사용자 확인을 받아요
    const unsubscription = graniteEvent.addEventListener('backEvent', {
      onEvent: () => {
        const shouldLeave = window.confirm('작성 중인 내용이 저장되지 않아요. 나가시겠어요?');
        if (shouldLeave) {
          // 나가는 코드를 작성해요.
        }
      },
      onError: (error) => {
        alert(`에러가 발생했어요: ${error}`);
      },
    });

    return unsubscription;
  }, []);

  return (
    <div>
      <h2>입력 폼</h2>
      <textarea
        value={formValue}
        onChange={(e) => setFormValue(e.target.value)}
        placeholder="여기에 내용을 입력해 주세요"
        rows={5}
        style={{ width: '100%' }}
      />
    </div>
  );
}
```

```tsx [React Native]
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

:::
