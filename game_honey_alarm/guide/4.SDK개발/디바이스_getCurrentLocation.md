---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/위치
  정보/getCurrentLocation.md
---

# 현재 위치 가져오기

## `getCurrentLocation`

디바이스의 현재 위치 정보를 가져오는 함수예요.
위치 기반 서비스를 구현할 때 사용되고, 한 번만 호출되어 현재 위치를 즉시 반환해요.
예를 들어 지도 앱에서 사용자의 현재 위치를 한 번만 가져올 때, 날씨 앱에서 사용자의 위치를 기반으로 기상 정보를 제공할 때, 매장 찾기 기능에서 사용자의 위치를 기준으로 가까운 매장을 검색할 때 사용하면 유용해요.

## 시그니처

```typescript
function getCurrentLocation(options: {
  accuracy: Accuracy;
}): Promise<Location>;
```

### 파라미터

### 프로퍼티

### 반환 값

## GetCurrentLocationPermissionError

위치 권한이 거부되었을 때 발생하는 에러예요. 에러가 발생했을 때 `error instanceof GetCurrentLocationPermissionError`를 통해 확인할 수 있어요.

## 시그니처

```typescript
class GetCurrentLocationPermissionError extends PermissionError {
    constructor();
}
```

## 예제

### 디바이스의 현재 위치 정보 가져오기

"권한 확인하기"버튼을 눌러서 현재 위치정보 권한을 확인해요.
사용자가 권한을 거부했거나 시스템에서 권한이 제한된 경우에는 [`GetCurrentLocationPermissionError`](./GetCurrentLocationPermissionError)를 반환해요.
"권한 요청하기"버튼을 눌러서 위치정보 권한을 요청할 수 있어요.

::: code-group

```tsx [React]
import { Accuracy, getCurrentLocation, Location } from '@apps-in-toss/web-framework';
import { useState } from 'react';


// 현재 위치 정보를 가져와 화면에 표시하는 컴포넌트
function CurrentPosition() {
  const [position, setPosition] = useState<Location | null>(null);

  const handlePress = async () => {
    try {
      const response = await getCurrentLocation({ accuracy: Accuracy.Balanced });
      setPosition(response);
    } catch (error) {
      console.error('위치 정보를 가져오는 데 실패했어요:', error);
    }
  };

  return (
    <div>
      {position ? (
        <span>
          위치: {position.coords.latitude}, {position.coords.longitude}
        </span>
      ) : (
        <span>위치 정보를 아직 가져오지 않았어요</span>
      )}
      <input type="button" value="현재 위치 정보 가져오기" onClick={handlePress} />
      <input type="button"
        value="권한 확인하기"
        onClick={async () => {
          alert(await getCurrentLocation.getPermission());
        }}
      />
      <input type="button"
        value="권한 요청하기"
        onClick={async () => {
          alert(await getCurrentLocation.openPermissionDialog());
        }}
      />
    </div>
  );
}
```

```tsx [React Native]
import { Accuracy, getCurrentLocation, Location } from '@apps-in-toss/framework';
import { useState } from 'react';
import { Alert, Button, Text, View } from 'react-native';

// 현재 위치 정보를 가져와 화면에 표시하는 컴포넌트
function CurrentPosition() {
  const [position, setPosition] = useState<Location | null>(null);

  const handlePress = async () => {
    try {
      const response = await getCurrentLocation({ accuracy: Accuracy.Balanced });
      setPosition(response);
    } catch (error) {
      console.error('위치 정보를 가져오는 데 실패했어요:', error);
    }
  };

  return (
    <View>
      {position ? (
        <Text>
          위치: {position.coords.latitude}, {position.coords.longitude}
        </Text>
      ) : (
        <Text>위치 정보를 아직 가져오지 않았어요</Text>
      )}
      <Button title="현재 위치 정보 가져오기" onPress={handlePress} />
      <Button
        title="권한 확인하기"
        onPress={async () => {
          Alert.alert(await getCurrentLocation.getPermission());
        }}
      />
      <Button
        title="권한 요청하기"
        onPress={async () => {
          Alert.alert(await getCurrentLocation.openPermissionDialog());
        }}
      />
    </View>
  );
}

```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-location-once](https://github.com/toss/apps-in-toss-examples/tree/main/with-location-once) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
