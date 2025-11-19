---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/네트워크/getNetworkStatus.md
---

# 네트워크 연결 상태 확인하기

## `getNetworkStatus`

`getNetworkStatus` 는 디바이스의 현재 네트워크 연결 상태를 가져오는 함수예요.
반환 값은 `NetworkStatus` 타입으로, 인터넷 연결 여부와 연결 유형(Wi-Fi, 모바일 데이터 등)을 나타내요. 값은 다음 중 하나예요.

* `OFFLINE`: 인터넷에 연결되지 않은 상태예요.
* `WIFI`: Wi-Fi에 연결된 상태예요.
* `2G`: 2G 네트워크에 연결된 상태예요.
* `3G`: 3G 네트워크에 연결된 상태예요.
* `4G`: 4G 네트워크에 연결된 상태예요.
* `5G`: 5G 네트워크에 연결된 상태예요.
* `WWAN`: 인터넷은 연결되었지만, 연결 유형(Wi-Fi, 2G~5G)을 알 수 없는 상태예요. 이 상태는 iOS에서만 확인할 수 있어요.
* `UNKNOWN`: 인터넷 연결 상태를 알 수 없는 상태예요. 이 상태는 안드로이드에서만 확인할 수 있어요.

## 시그니처

```typescript
function getNetworkStatus(): Promise<NetworkStatus>;
```

### 반환 값

## 예제

### 현재 네트워크 상태 가져오기

네트워크 연결 상태를 가져와 화면에 표시하는 예제예요.

```tsx
import { useState, useEffect } from 'react';
import { Text, View } from 'react-native';
import { getNetworkStatus, NetworkStatus } from '@apps-in-toss/framework';

function GetNetworkStatus() {
  const [status, setStatus] = useState<NetworkStatus | ''>('');

  useEffect(() => {
    async function fetchStatus() {
      const networkStatus = await getNetworkStatus();
      setStatus(networkStatus);
    }

    fetchStatus();
  }, []);

  return (
    <View>
      <Text>현재 네트워크 상태: {status}</Text>
    </View>
  );
}
```

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-network-status](https://github.com/toss/apps-in-toss-examples/tree/main/with-network-status) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
