---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/safe-area.md
---

# Safe Area 여백 값 구하기

모바일 브라우저에서는 상태바나 홈 인디케이터 같은 시스템 UI 때문에 콘텐츠가 가려질 때가 있어요.\
앱인토스 SDK는 이런 상황을 방지하기 위해 화면의 안전 영역(Safe Area) 여백 값을 픽셀 단위로 계산하는 함수를 제공해요.

특히 iPhone X 이상 기기나 일부 Android 기기에서는 전체 화면을 사용하는 웹 앱에서 시스템 UI가 콘텐츠를 가리는 경우가 자주 있어요.\
아래 함수를 사용하면 콘텐츠가 안전하게 표시되도록 여백을 쉽게 조절할 수 있어요.

## `SafeAreaInsets`

화면 모드가 바뀔 때 `safearea` 값을 확인할 수 있어요.\
화면 전환 시 안전 영역 정보를 가져오거나, 변경을 구독할 수도 있어요.\
이 기능을 사용하면 다양한 디바이스 환경에서도 안정적인 UI를 구현할 수 있어요.

* `SafeAreaInsets.get()` : 현재 화면 모드의 `safearea` 값을 가져와요.
* `SafeAreaInsets.subscribe()` : 화면 모드가 바뀔 때마다 `safearea` 값 변화를 구독해요.

### 예시

```tsx
import { SafeAreaInsets } from '@apps-in-toss/web-framework';
import { useEffect, useState } from 'react';

interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

function Page() {
  const [safeAreaInsetsValue, setSafeAreaInsetsValue] = useState<SafeAreaInsets>(() => SafeAreaInsets.get())
  // 네비게이션 바 X 버튼 위치
  // 네비게이션 바 상단 여백: safeAreaInsetsValue.top
  // 네비게이션 바 우측 여백: safeAreaInsetsValue.right + 10


  useEffect(() => {
    const cleanup = SafeAreaInsets.subscribe({
      onEvent: (insets) => {
        setSafeAreaInsetsValue(insets);
      }
    });
    return () => cleanup();
  }, []);

  // ...
}
```

## `getSafeAreaInsets`

::: tip 이 함수는 SDK 1.4.6 버전까지만 사용할 수 있어요
**1.4.7 버전 부터는 deprecated** 되었어요
:::

```ts
import { getSafeAreaInsets } from "@apps-in-toss/web-framework";

const insets = getSafeAreaInsets();
// 예시 반환값: { top: 44, bottom: 34 }
```

반환되는 객체는 다음 속성을 포함해요.

* `top`: 상단 상태바에 가리지 않도록 확보해야 하는 여백이에요.
* `bottom`: 하단 홈 인디케이터에 가리지 않도록 확보해야 하는 여백이에요.

이 값은 전체 화면(`viewport`)에 맞춰 UI를 만들 때 자주 사용돼요.\
예를 들어, 하단 고정 버튼에 여백을 주거나 상단 헤더가 상태바에 겹치지 않도록 만들 수 있어요.

### 하단 여백 적용 예시

하단 고정 버튼이 홈 인디케이터에 겹치지 않도록 여백을 주는 예시예요.

```tsx
import { getSafeAreaInsets } from "@apps-in-toss/web-framework";

const insets = getSafeAreaInsets();

const Button = () => {
  return (
    <div style={{ paddingBottom: `${insets.bottom}px` }}>
      <button>확인</button>
    </div>
  );
};
```

### 상단 여백 적용 예시

상단 고정 헤더가 상태바에 겹치지 않도록 여백을 주는 예시예요.

```tsx
import { getSafeAreaInsets } from "@apps-in-toss/web-framework";

const insets = getSafeAreaInsets();

const Header = () => {
  return (
    <div style={{ paddingTop: `${insets.top}px` }}>
      <h1>제목</h1>
    </div>
  );
};
```

## `useSafeAreaInsets`

모바일 브라우저에서 상태바나 홈 인디케이터 같은 시스템 UI에 의해 콘텐츠가 가려지는 문제를 방지할 수 있도록, 화면의 안전 영역(Safe Area) 여백 값을 픽셀 단위로 계산해줘요.\
`useSafeAreaInsets` 는 ReactNative 로 개발할 때 사용할 수 있어요.

```tsx
import { useSafeAreaInsets } from '@granite-js/native/react-native-safe-area-context';
const { top: safeAreaTop, right: safeAreaRight } = useSafeAreaInsets();
// 네비바 상단 여백: safeAreaTop
// 네비바 우측 여백: safeAreaRight + 10
```
