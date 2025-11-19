---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/게임/grantPromotionRewardForGame.md
---

# 게임 프로모션(토스 포인트)

## `grantPromotionRewardForGame`

`grantPromotionRewardForGame` 함수는 [`getUserKeyForGame`](/bedrock/reference/framework/게임/getUserKeyForGame.md) 으로부터 받은 **유저 식별자 (`hash`)를 사용해 프로모션(토스 포인트) 기능을 실행하는 함수**예요.\
별도의 서버 연동 없이도 **게임 미니앱 내에서 유저에게 토스 포인트를 지급**하고, 혜택탭에 노출할 수 있어요.

이 함수는 **게임 카테고리 미니앱에서만 호출할 수 있으며,** 비게임 카테고리에서 실행하면 오류가 발생해요.

::: info 프로모션 기능
앱인토스의 프로모션은 **사용자의 특정 행동을 기준으로 토스 포인트를 지급하는 이벤트 기능**이에요.\
프로모션은 **비즈 월렛에 충전한 예산으로 진행**할 수 있으며, **혜택 탭 노출 여부를 콘솔에서 설정**할 수 있어요.\
[프로모션 기능 이해하기](/promotion/intro.md)\
[프로모션 기능 콘솔 가이드](/promotion/console.md)\
:::

::: tip 주의하세요

* **토스앱 5.232.0 버전 이상**에서 지원해요.\
  해당 버전 미만에서는 `undefined`가 반환돼요.
* 모든 사용자의 식별자를 안정적으로 확보하기 위해 **토스앱 최소 지원 버전을 5.232.0으로 상향**했어요.
  * 최소 버전 미만에서는 미니앱 진입 시 업데이트 안내 화면이 표시돼요.
* 게임 유저 식별자는 **게임사 내부 식별용 키**로만 사용되며, 이 키로 토스 서버에 직접 요청할 수 없어요.
* **프로모션 기능을 개발한 후, 실제 프로모션을 시작하기 전에 테스트용 프로모션 코드로 최소 1회 이상 호출해야 합니다.**\
  (테스트 호출을 통해 프로모션이 정상적으로 등록 및 승인 상태로 전환돼요.)
  :::

## 시그니처

```typescript
function grantPromotionRewardForGame({ params, }: {
    params: {
        promotionCode: string;
        amount: number;
    };
}): Promise<GrantPromotionRewardForGameResult>;
```

### 파라미터

### 반환 값

포인트 지급 결과를 반환해요.

* `{ key: string }`: 포인트 지급에 성공했어요. key는 리워드 키를 의미해요.
* `{ errorCode: string, message: string }`: 포인트 지급에 실패했어요. 에러 코드를 확인해 주세요.

### 에러 코드

프로모션 함수 사용 중 발생할 수 있는 에러 코드 목록입니다.\
응답 코드나 메시지를 참고해 **적절한 예외 처리 로직**을 적용해 주세요.

::: tip `4109` 에러가 발생한다면?

* 프로모션 예산의 **80% 소진이 이메일로 안내**가 발송돼요.
* 프로모션을 계속 진행하려면 **콘솔에서 예산을 증액**해 주세요.
* 예산이 부족할 경우, **비즈월렛에서 금액을 충전**해 예산을 늘릴 수 있어요.
* 예산이 모두 소진되면 프로모션이 **자동으로 종료되어 `4109` 에러가 발생**해요.
* 예산 부족으로 인해 포인트 지급이 실패하면 **사용자 CS 이슈로 이어질 수 있으니 주의**해 주세요.
  :::

| 코드 | 메시지 | 발생 원인 / 대응 방법 |
|------|--------|-------------------|
| `40000`| |게임이 아닌 미니앱에서 호출한 경우|
| `4100` | 프로모션 정보를 찾을 수 없어요 | 콘솔에 등록되지 않은 프로모션 키로 호출한 경우|
| `4109` | 프로모션이 실행중이 아니에요 | 콘솔에서 프로모션을 시작하지 않았거나, 예산이 모두 소진되어 자동 종료된 경우|
| `4110` | 리워드를 지급/회수할 수 없어요 | 내부 시스템 오류 발생한 경우로, **재지급 로직**을 적용해 주세요. |
| `4111` | 리워드 지급내역을 찾을 수 없어요 |존재하지 않은 지급 내역을 조회한 경우|
| `4112` | 프로모션 머니가 부족해요 |예산 부족으로 지급이 실패한 경우로, 콘솔에서 예산 증액 또는 비즈월렛 충전 필요|
| `4114` | 1회 지급 금액을 초과했어요 ||
| `4116` | 최대 지급 금액이 예산을 초과했어요 ||
|`ERROR`|알 수 없는 오류가 발생했어요.||
|`undefined`|앱 버전이 최소 지원 버전보다 낮아요.||

## 예제

::: code-group

```tsx [React]
// webview
import { grantPromotionRewardForGame } from '@apps-in-toss/web-framework';

function GrantRewardButton() {
  async function handleClick() {
      const result = await grantPromotionRewardForGame({
        params: {
          promotionCode: 'GAME_EVENT_2024',
          amount: 1000,
        },
      });

      if (!result) {
        console.warn('지원하지 않는 앱 버전이에요.');
        return;
      }

      if (result === 'ERROR') {
        console.error('포인트 지급 중 알 수 없는 오류가 발생했어요.');
        return;
      }

      if ('key' in result) {
        console.log('포인트 지급 성공!', result.key);
      } else if ('errorCode' in result) {
        console.error('포인트 지급 실패:', result.errorCode, result.message);
      }
  }

  return (
    <button onClick={handleClick}>포인트 지급하기</button>
  );
}
```

```tsx [React Native]
// react-native
import { Button } from 'react-native';
import { grantPromotionRewardForGame } from '@apps-in-toss/framework';

function GrantRewardButton() {
  async function handlePress() {
      const result = await grantPromotionRewardForGame({
        params: {
          promotionCode: 'GAME_EVENT_2024',
          amount: 1000,
        },
      });

      if (!result) {
        console.warn('지원하지 않는 앱 버전이에요.');
        return;
      }

      if (result === 'ERROR') {
        console.error('포인트 지급 중 알 수 없는 오류가 발생했어요.');
        return;
      }

      if ('key' in result) {
        console.log('포인트 지급 성공!', result.key);
      } else if ('errorCode' in result) {
        console.error('포인트 지급 실패:', result.errorCode, result.message);
      }
  }

  return <Button onPress={handlePress} title="포인트 지급하기" />;
}
```

:::
