---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/이벤트
  제어/entry-message-exited.md
---

# 앱 진입 완료 이벤트 감지하기

## `appsInTossEvent`

`appsInTossEvent`를 사용하면 토스 앱에서 전달되는 다양한 상태 이벤트를 처리할 수 있어요.

그중 `entryMessageExited` 이벤트는 앱 진입 직후 표시되는 "ㅇㅇ으로 이동했어요"와 같은 안내 메시지가 화면에서 사라지는 시점을 알려줘요.

## 해결하는 문제

* 앱 진입 시 표시된 안내 메시지가 사라진 정확한 순간을 감지할 수 있어요.
* 메시지가 사라진 직후, 초기화 작업이나 데이터 로딩을 정확한 타이밍에 실행할 수 있어요.
* 사용자가 앱을 정상적으로 이용할 준비가 완료됐음을 명확히 할 수 있어요.

## 동작 방식

`appsInTossEvent.addEventListener('entryMessageExited', options)`를 사용해서 이벤트를 구독할 수 있어요.

* `onEvent`: 안내 메시지가 화면에서 사라지는 즉시 호출돼요. 이 시점에 초기화 작업을 실행할 수 있어요.

구독한 리스너는 반환된 `unsubscription` 함수를 호출해서 해제할 수 있어요.

## 사용 예시

안내 메시지가 사라진 직후 게임을 시작하는 예시예요.

::: code-group

```tsx [React]
import { appsInTossEvent } from '@apps-in-toss/web-framework';
import { useEffect } from 'react';

/**
 * 안내 메시지가 사라진 시점에 게임을 시작하는 컴포넌트예요.
 *
 * @example
 * import { GameStarter } from './GameStarter';
 *
 * const App = () => <GameStarter />;
 */
function GameStarter() {
  useEffect(() => {
    const unsubscription = appsInTossEvent.addEventListener('entryMessageExited', {
      onEvent: () => {
        // 진입 메시지가 사라진 직후 게임 시작
        startGame();
      },
      onError: (error) => {
        console.error('게임 시작 이벤트 처리 중 오류:', error);
      },
    });

    return () => {
      unsubscription();
    };
  }, []);

  /**
   * 게임을 시작하는 함수예요.
   * 타이머 시작, 캐릭터 등장 등 초기 게임 로직을 이곳에 작성해요.
   */
  const startGame = () => {
    console.log('게임을 시작합니다!');
    // 게임 시작 로직 추가
  };

  return (
    <div>
      <h2>게임을 준비 중...</h2>
    </div>
  );
}
```

```tsx [React Native]
import { appsInTossEvent } from '@apps-in-toss/framework';
import { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';

/**
 * 안내 메시지가 사라진 시점에 게임을 시작하는 컴포넌트예요.
 *
 * @example
 * import { GameStarter } from './GameStarter';
 *
 * const App = () => <GameStarter />;
 */
function GameStarter() {
  useEffect(() => {
    const unsubscription = appsInTossEvent.addEventListener('entryMessageExited', {
      onEvent: () => {
        // 진입 메시지가 사라진 직후 게임 시작
        startGame();
      },
      onError: (error) => {
        console.error('게임 시작 이벤트 처리 중 오류:', error);
      },
    });

    return () => {
      unsubscription();
    };
  }, []);

  /**
   * 게임을 시작하는 함수예요.
   * 타이머 시작, 캐릭터 등장 등 초기 게임 로직을 이곳에 작성해요.
   */
  const startGame = () => {
    console.log('게임을 시작합니다!');
    // 게임 시작 로직 추가
  };

  return (
    <View>
      <Text>게임을 준비 중...</Text>
    </View>
  );
}
```
