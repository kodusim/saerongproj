---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/토스페이/TossPay.md
---

# 토스 페이

## `TossPay`

`TossPay`는 토스페이 결제 관련 함수를 모아둔 객체예요.

### 시그니처

```typescript
TossPay: {
  checkoutPayment: typeof checkoutPayment;
}
```

### 프로퍼티

## `checkoutPayment`

`checkoutPayment` 함수는 토스페이 결제창을 띄우고, 사용자 인증을 수행해요. 인증이 완료되면 성공 여부를 반환해요.

이 함수는 결제창을 통해 사용자 인증만 해요. 실제 결제 처리는 인증 성공 후 서버에서 별도로 해야 해요.

### 시그니처

```typescript
function checkoutPayment(options: CheckoutPaymentOptions): Promise<CheckoutPaymentResult>;
```

### 파라미터

### 반환 값

### 예제

토스페이 결제창 띄우고 인증 처리하기

::: code-group

```tsx [React]
import { checkoutPayment } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';

function TossPayButton() {
  async function handlePayment() {
    try {
      // 실제 구현 시 결제 생성 역할을 하는 API 엔드포인트로 대체해주세요.
      const { payToken } = await fetch('/my-api/payment/create').then((res) => res.json());

      const { success, reason } = await checkoutPayment({ payToken });

      if (success) {
        // 실제 구현 시 결제를 실행하는 API 엔드포인트로 대체해주세요.
        await fetch('/my-api/payment/execute', {
          method: 'POST',
          body: JSON.stringify({ payToken }),
          headers: { 'Content-Type': 'application/json' },
        });
      } else {
        console.log('인증 실패:', reason);
      }
    } catch (error) {
      console.error('결제 인증 중 오류가 발생했어요:', error);
    }
  }

  return <Button onClick={handlePayment}>결제하기</Button>;
}
```

```tsx [React Native]
import { TossPay } from '@apps-in-toss/framework';
import { Button } from '@toss/tds-react-native';

function TossPayButton() {
  async function handlePayment() {
    try {
      // 실제 구현 시 결제 생성 역할을 하는 API 엔드포인트로 대체해주세요.
      const { payToken } = await fetch('/my-api/payment/create').then((res) => res.json());

      const { success, reason } = await TossPay.checkoutPayment({ payToken });

      if (success) {
        // 실제 구현 시 결제를 실행하는 API 엔드포인트로 대체해주세요.
        await fetch('/my-api/payment/execute', {
          method: 'POST',
          body: JSON.stringify({ payToken }),
          headers: { 'Content-Type': 'application/json' },
        });
      } else {
        console.log('인증 실패:', reason);
      }
    } catch (error) {
      console.error('결제 인증 중 오류가 발생했어요:', error);
    }
  }

  return <Button onPress={handlePayment}>결제하기</Button>;
}
```

:::

## `CheckoutPaymentOptions`

`CheckoutPaymentOptions` 는 토스페이 결제창을 띄울 때 필요한 옵션이에요.

### 시그니처

```typescript
interface CheckoutPaymentOptions {
  payToken: string;
}
```

### 프로퍼티

## `CheckoutPaymentResult`

`CheckoutPaymentResult` 는 토스페이 결제창에서 사용자가 인증에 성공했는지 여부예요.

### 시그니처

```typescript
interface CheckoutPaymentResult {
  success: boolean;
  reason?: string;
}
```

### 프로퍼티
