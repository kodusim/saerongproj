---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/환경
  확인/getDeviceId.md
---

# 기기 고유식별자 확인하기

## `getDeviceId`

`getDeviceId` 함수는 사용 중인 기기의 고유 식별자를 문자열로 반환해요.

이 함수는 현재 사용 중인 기기의 고유 식별자를 문자열로 반환해요. 기기별로 설정이나 데이터를 저장하거나 사용자의 기기를 식별해서 로그를 기록하고 분석하는 데 사용할 수 있어요. 같은 사용자의 여러 기기를 구분하는 데도 유용해요.

## 시그니처

```typescript
function getDeviceId(): string;
```

### 반환 값

## 예제

### 기기 고유 식별자 가져오기

::: code-group

```tsx [React]
import { getDeviceId } from "@apps-in-toss/web-framework";
import { useState } from "react";

const DeviceInfo = () => {
  const [deviceId, setDeviceId] = useState<string | null>(null);

  const fetchDeviceId = async () => {
    setDeviceId(getDeviceId());
  };

  return (
    <div>
      <button onClick={fetchDeviceId}>기기 ID 가져오기</button>
      {deviceId && <p>Device ID: {deviceId}</p>}
    </div>
  );
};
}
```

```tsx [React Native]
import { getDeviceId } from '@apps-in-toss/framework';
import { Text } from '@toss/tds-react-native';

function MyPage() {
  const id = getDeviceId();

  return <Text>사용자의 기기 고유 식별자: {id}</Text>;
}
```

:::
