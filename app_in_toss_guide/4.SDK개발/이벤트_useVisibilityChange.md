---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/useVisibilityChange.md
---

# 가시성 변경 감지하기

## `useVisibilityChange`

`useVisibilityChange` 훅을 사용하면 페이지나 컴포넌트가 사용자에게 보이는지 여부가 변경될 때 이를 감지할 수 있어요. 화면이 보이는 상태가 바뀌면 전달된 콜백 함수가 호출돼요. 예를 들어, 사용자가 다른 탭으로 이동하거나, 창을 최소화할 때 콜백이 호출돼요.

반환값이 `true`이면 `visible`, `false`이면 `hidden` 문자열이 전달돼요.

::: info 참고하세요
WebView에서 앱이 백그라운드로 전환되었을 때 콜백 함수를 등록하는 방법은 [visibilitychange](https://developer.mozilla.org/en-US/docs/Web/API/Document/visibilitychange_event)를 활용할 수 있어요.\
자세한 내용은 MDN Web Docs를 참고해 주세요.
:::

## 시그니처

```typescript
function useVisibilityChange(callback: VisibilityCallback): void;
```

### 파라미터

## 예제

### 화면의 보이는 상태가 변경될 때 로그를 남기는 예제

아래 코드는 화면의 보이는 상태가 변경될 때 `visibilityState` 값을 `console.log`로 기록하는 예시예요.

* 홈 화면으로 이동하면 `hidden`, 다시 돌아오면 `visible`을 기록해요.
* 외부 링크(`https://toss.im`)로 이동하면 `hidden`을 기록하고, 다시 돌아오면 `visible`을 기록해요.

```tsx{1,5-7}
import { useVisibilityChange } from '@granite-js/react-native';
import { Button, Linking } from 'react-native';

export default function ImagePage() {
  useVisibilityChange((visibilityState) => {
    console.log({ visibilityState });
  });

  return (
    <Button
      onPress={() => {
        Linking.openURL('https://toss.im');
      }}
      title="https://toss.im 이동"
    />
  );
}

/**
 * 출력 예시:
 * { "visibilityState": "hidden" }
 * { "visibilityState": "visible" }
 * { "visibilityState": "hidden" }
 * { "visibilityState": "visible" }
 */
```
