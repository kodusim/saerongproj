---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/useVisibility.md
---

# 화면 보임 여부 확인하기

## `useVisibility`

`useVisibility` 훅을 사용하면 화면이 현재 사용자에게 보이는지 여부를 알 수 있어요. 사용자가 화면을 보고 있을 때만 특정 작업을 실행하거나, 로그를 남길 수 있어요.

앱의 화면이 현재 사용자에게 보인다면 `true`를 반환하고, 보이지 않는다면 `false`를 반환해요. 단, 시스템 공유하기 모달([share](/bedrock/reference/framework/공유/share))을 열고 닫을 때는 화면이 보이는 상태가 바뀌지 않아요.

사용 예시는 다음과 같아요.

* 다른 앱으로 전환하거나 홈 버튼을 누르면 `false` 를 반환해요.
* 다시 토스 앱으로 돌아오거나 화면이 보이면 `true` 를 반환해요.
* 토스 앱 내 다른 서비스로 이동하면 `false` 를 반환해요.

## 시그니처

```typescript
function useVisibility(): boolean;
```

### 반환 값

## 예제

### 화면이 보이는 상태를 확인하는 예제

아래 코드는 화면이 사용자에게 보였을 때 `visibility` 값을 `console.log`로 확인하는 예시예요.

* 홈 화면으로 이동하면 `false`가 기록되고, 다시 돌아오면 `true`가 기록돼요.
* 외부 링크(`https://toss.im`)로 이동하면 `false`가 기록되고, 다시 돌아오면 `true`가 기록돼요.

```tsx{1,6,8-12}
import { useVisibility } from '@granite-js/react-native';
import { useEffect } from 'react';
import { Button, Linking } from 'react-native';

export default function VisibilityPage() {
  const visibility = useVisibility();

  useEffect(() => {
    console.log({
      visibility,
    });
  }, [visibility]);

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
 * { "visibility": false }
 * { "visibility": true }
 * { "visibility": false }
 * { "visibility": true }
 */
```
