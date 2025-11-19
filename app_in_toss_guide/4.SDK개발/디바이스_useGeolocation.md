---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/위치
  정보/useGeolocation.md
---

# 훅으로 위치 사용하기

## `useGeolocation`

`useGeolocation` 는 디바이스의 위치 정보를 반환하는 훅이에요. 위치가 변경되면 값도 변경돼요.
GPS 정보를 활용해 현재 위치를 감지하고, 사용자의 이동에 따라 자동으로 업데이트돼요.
예를 들어, 지도 기반 서비스에서 사용자의 현재 위치를 표시하거나, 배달 앱에서 실시간 이동 경로를 추적할 때 활용할 수 있어요.
위치 정보의 정확도와 업데이트 주기를 조정할 수 있어서 배터리 소모를 최소화하면서도 필요한 수준의 정확도를 유지할 수 있어요.

## 시그니처

```typescript
function useGeolocation({ accuracy, distanceInterval, timeInterval }: UseGeolocationOptions): Location | null;
```

### 파라미터

### 반환 값

## 예제

### 위치 정보 변경 감지하기

```tsx
import React, { useState, useCallback } from 'react';
import { View, Text } from 'react-native';
import { useGeolocation, Accuracy } from '@apps-in-toss/framework';

// 위치 정보 변경 감지하기
function LocationWatcher() {
  const location = useGeolocation({
    accuracy: Accuracy.Balanced,
    distanceInterval: 10,
    timeInterval: 1000,
  });

  if (location == null) {
    return <Text>위치 정보를 가져오는 중이에요...</Text>;
  }

  return (
    <View>
      <Text>위치 정보: {location.latitude}, {location.longitude}</Text>
    </View>
  );
}
```

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-location-tracking](https://github.com/toss/apps-in-toss-examples/tree/main/with-location-tracking) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
