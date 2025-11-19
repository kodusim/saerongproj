---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/환경
  확인/getOperationalEnvironment.md
---

# 애플리케이션 환경 확인하기

## `getOperationalEnvironment`

`getOperationalEnvironment` 함수로 애플리케이션의 환경 정보를 사용해서 애플리케이션이 현재 어느 배포 환경(예: `sandbox`, `toss`)에서 실행 중인지 확인할 수 있어요.\
토스 앱에서 실행 중이라면 `'toss'`, 샌드박스 환경에서 실행 중이라면 `'sandbox'`를 반환해요.

운영 환경은 앱이 실행되는 컨텍스트를 의미하며, 특정 기능의 사용 가능 여부를 판단하는 데 활용할 수 있어요.

## 시그니처

```typescript
function getOperationalEnvironment(): 'toss' | 'sandbox';
```

### 반환 값

현재 운영 환경을 나타내는 문자열이에요.

* `'toss'`: 토스 앱에서 실행 중이에요.
* `'sandbox'`: 샌드박스 환경에서 실행 중이에요.

## 예제

### 현재 운영 환경 확인하기

애플리케이션이 배포된 환경에 따라 실행 환경이 달라질 수 있어요. 예를 들어, `sandbox` 환경에서는 일부 테스트 기능을 제공하고, `toss` 환경에서는 실제 서비스를 제공할 수 있어요. 실행 환경을 확인하면 이러한 기능 차이를 관리할 수 있죠.

다음은 실행 환경을 확인하는 예시예요.

::: code-group

```tsx [React]
import { getOperationalEnvironment } from '@apps-in-toss/web-framework';
import { Text } from '@toss/tds-mobile';

function EnvironmentInfo() {
  const environment = getOperationalEnvironment();

  return <Text>{`현재 실행 환경은 '${environment}'입니다.`}</Text>;
}
```

```tsx [React Native]
import { getOperationalEnvironment } from '@apps-in-toss/framework';
import { Text } from '@toss/tds-react-native';

function EnvironmentInfo() {
  const environment = getOperationalEnvironment();

  return <Text>{`현재 실행 환경은 '${environment}'입니다.`}</Text>;
}
```

:::

## 실행 환경에 따라 기능 제한하기

특정 배포 환경에서만 제공해야 하는 기능이 있을 수 있어요. 아래는 `sandbox` 환경에서만 특별한 기능을 제공하는 예시예요.

```tsx{4,8-9}
import { View, Text } from 'react-native';
import { getOperationalEnvironment } from '@apps-in-toss/framework';

const isSandbox = getOperationalEnvironment() === 'sandbox'; // 'sandbox' 환경인지 확인하는 변수

function Component() {
  const handlePress = () => {
    if (isSandbox) {
      // 'sandbox' 환경에서 제공할 기능
    } else {
      // 다른 환경에서 제공할 기능
    }
  };

  return <Button onPress={handlePress}>자세히 보기</Button>;
}
```
