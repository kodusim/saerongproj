---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/친구초대/contactsViral.md
---

# 공유 리워드

## `contactsViral`

`contactsViral` 함수는 친구에게 공유하고 리워드를 받을 수 있는 기능을 제공해요. 사용자가 친구에게 공유를 완료하면, 앱 브릿지를 통해 이벤트가 전달되고, 해당 이벤트를 기반으로 리워드 정보를 받을 수 있어요.

::: tip 주의하세요

* 본 기능은 토스앱 5.223.0 버전부터 지원해요. 하위 버전에서는 `undefined`가 반환됩니다.
* 기능 사용을 위해서는 미니앱 승인이 반드시 필요합니다. 미승인 상태에서는 `Internal Server Error`가 발생합니다.

:::

::: info 참고하세요

* 테스트 환경(샌드박스 앱)에서는 빈 화면으로 보여요. 리워드 지급 버튼을 눌러도 실제로 동작하지 않아요.
* 콘솔 내 QR코드로 테스트를 진행해 주세요.
* 콘솔에 등록된 리워드 ID를 활용하여 테스트를 할 수 있어요.
* 친구 목록은 상호 연락처 저장 여부 외에도 다음 조건에 따라 달라질 수 있어요
  * 마케팅 수신 동의 여부
  * 야간 마케팅 수신 동의 여부
  * 푸시 토큰 등록 여부
  * 연락처 알림 차단 여부
    :::

### 시그니처

```ts
function contactsViral(params: ContactsViralParams): () => void;
```

### 파라미터

### 반환값

### 예제

::: code-group

```tsx [React]
import { contactsViral } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';
import { useCallback } from 'react';

function ContactsViralButton({ moduleId }: { moduleId: string }) {
  const handleContactsViral = useCallback(() => {
    try {
      const cleanup = contactsViral({
        options: { moduleId: moduleId.trim() },
        onEvent: (event) => {
          if (event.type === 'sendViral') {
            console.log('리워드 지급:', event.data.rewardAmount, event.data.rewardUnit);
          } else if (event.type === 'close') {
            console.log('모듈 종료:', event.data.closeReason);
          }
        },
        onError: (error) => {
          console.error('에러 발생:', error);
        },
      });

      return cleanup;
    } catch (error) {
      console.error('실행 중 에러:', error);
    }
  }, [moduleId]);

  return <Button onClick={handleContactsViral}>친구에게 공유하고 리워드 받기</Button>;
}
```

```tsx [React Native]
import { contactsViral } from '@apps-in-toss/framework';
import { Button } from '@toss/tds-react-native';
import { useCallback } from 'react';

function ContactsViralButton({ moduleId }: { moduleId: string }) {
  const handleContactsViral = useCallback(() => {
    try {
      const cleanup = contactsViral({
        options: { moduleId: moduleId.trim() },
        onEvent: (event) => {
          if (event.type === 'sendViral') {
            console.log('리워드 지급:', event.data.rewardAmount, event.data.rewardUnit);
          } else if (event.type === 'close') {
            console.log('모듈 종료:', event.data.closeReason);
          }
        },
        onError: (error) => {
          console.error('에러 발생:', error);
        },
      });

      return cleanup;
    } catch (error) {
      console.error('실행 중 에러:', error);
    }
  }, [moduleId]);

  return <Button onPress={handleContactsViral}>친구에게 공유하고 리워드 받기</Button>;
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-contacts-viral](https://github.com/toss/apps-in-toss-examples/tree/main/with-contacts-viral) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.

## `ContactsViralOption`

`ContactsViralOption`는 [연락처 공유 기능](/bedrock/reference/framework/친구초대/contactsViral.md)을 사용할 때 필요한 옵션이에요.

### 시그니처

```ts
type ContactsViralOption = {
  moduleId: string;
};
```

### 프로퍼티

## `ContactsViralParams`

`ContactsViralParams` 는 `contactsViral` 함수를 실행할 때 사용하는 파라미터 타입이에요. 옵션을 설정하고, 이벤트 및 에러 처리 콜백을 지정할 수 있어요.

### 시그니처

```ts
interface ContactsViralParams {
  options: ContactsViralOption;
  onEvent: (event: ContactsViralEvent) => void;
  onError: (error: unknown) => void;
}
```

### 프로퍼티

## `ContactsViralSuccessEvent`

`ContactsViralSuccessEvent` 는 연락처 공유 모듈이 정상적으로 종료됐을 때 전달되는 이벤트 객체예요. 종료 이유와 함께 리워드 상태 및 남은 친구 수 등 관련 정보를 제공해요.

### 시그니처

```ts
type ContactsViralSuccessEvent = {
  type: 'close';
  data: {
    closeReason: 'clickBackButton' | 'noReward';
    sentRewardAmount?: number;
    sendableRewardsCount?: number;
    sentRewardsCount: number;
    rewardUnit?: string;
  };
};
```

### 프로퍼티

### 예제

모듈 종료 이벤트 처리하기

```ts
contactsViral({
  options: { moduleId: 'your-module-id' },
  onEvent: (event) => {
    if (event.type === 'close') {
      console.log('종료 사유:', event.data.closeReason);
      console.log('공유 완료한 친구 수:', event.data.sentRewardsCount);
    }
  },
  onError: (error) => {
    console.error('에러 발생:', error);
  },
});
```

## `RewardFromContactsViralEvent`

`RewardFromContactsViralEvent` 는 친구에게 공유하기를 완료했을 때 지급할 리워드 정보를 담는 타입이에요. 이 타입을 사용하면 공유가 완료됐을 때 지급할 리워드 정보를 확인할 수 있어요.

### 시그니처

```ts
type RewardFromContactsViralEvent = {
  type: 'sendViral';
  data: {
    rewardAmount: number;
    rewardUnit: string;
  };
};
```

### 프로퍼티

### 예제

공유 완료 후 리워드 정보 처리하기

```ts
contactsViral({
  options: { moduleId: 'your-module-id' },
  onEvent: (event) => {
    if (event.type === 'sendViral') {
      console.log('리워드 지급:', event.data.rewardAmount, event.data.rewardUnit);
    }
  },
  onError: (error) => {
    console.error('에러 발생:', error);
  },
});
```
