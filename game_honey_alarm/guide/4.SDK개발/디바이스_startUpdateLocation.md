---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/위치
  정보/startUpdateLocation.md
---

# 실시간 위치 추적하기

## `startUpdateLocation`

디바이스의 위치 정보를 지속적으로 감지하고, 위치가 변경되면 콜백을 실행하는 함수예요. 콜백 함수를 등록하면 위치가 변경될 때마다 자동으로 호출돼요.
실시간 위치 추적이 필요한 기능을 구현할 때 사용할 수 있어요. 예를 들어 지도 앱에서 사용자의 현재 위치를 실시간으로 업데이트할 때, 운동 앱에서 사용자의 이동 거리를 기록할 때 등이에요.
위치 업데이트 주기와 정확도를 조정해 배터리 소모를 최소화하면서도 필요한 정보를 얻을 수 있어요.

## 시그니처

```typescript
function startUpdateLocation(options: {
  onError: (error: unknown) => void;
  onEvent: (location: Location) => void;
  options: StartUpdateLocationOptions;
}): () => void;
```

### 파라미터

### 프로퍼티

## StartUpdateLocationPermissionError

위치 업데이트 권한이 거부되었을 때 발생하는 에러예요. 에러가 발생했을 때 `error instanceof StartUpdateLocationPermissionError`를 통해 확인할 수 있어요.

## 시그니처

```typescript
StartUpdateLocationPermissionError: typeof GetCurrentLocationPermissionError
```

## 예제

### 위치 정보 변경 감지하기

위치 정보가 변경되는것을 감지하는 예제예요. "위치 정보 변경 감지하기"를 눌러서 감지할 수 있어요.

"권한 확인하기"버튼을 눌러서 현재 위치 정보 변경 감지 권한을 확인해요.
사용자가 권한을 거부했거나 시스템에서 권한이 제한된 경우에는 [`StartUpdateLocationPermissionError`](./StartUpdateLocationPermissionError)를 반환해요.
"권한 요청하기"버튼을 눌러서 위치 정보 변경 감지 권한을 요청할 수 있어요.

::: code-group

```tsx [React]
import { Accuracy, Location, startUpdateLocation, StartUpdateLocationPermissionError } from '@apps-in-toss/web-framework';
import { useCallback, useState } from 'react';


// 위치 정보 변경 감지하기
function LocationWatcher() {
  const [location, setLocation] = useState<Location | null>(null);

  const handlePress = useCallback(() => {
    startUpdateLocation({
      options: {
        accuracy: Accuracy.Balanced,
        timeInterval: 3000,
        distanceInterval: 10,
      },
      onEvent: (location) => {
        setLocation(location);
      },
      onError: (error) => {
        if (error instanceof StartUpdateLocationPermissionError) {
          // 위치 정보 변경 감지 권한 없음
        }
        console.error('위치 정보를 가져오는데 실패했어요:', error);
      },
    });
  }, []);

  return (
    <div>
      {location != null && (
        <>
          <span>위도: {location.coords.latitude}</span>
          <span>경도: {location.coords.longitude}</span>
          <span>위치 정확도: {location.coords.accuracy}m</span>
          <span>높이: {location.coords.altitude}m</span>
          <span>고도 정확도: {location.coords.altitudeAccuracy}m</span>
          <span>방향: {location.coords.heading}°</span>
        </>
      )}

      <input type="button" value="위치 정보 변경 감지하기" onClick={handlePress} />

      <input type="button"
        value="권한 확인하기"
        onClick={async () => {
          const permission = await startUpdateLocation.getPermission();
          alert(permission);
        }}
      />
      <input type="button"
        value="권한 요청하기"
        onClick={async () => {
          const permission = await startUpdateLocation.openPermissionDialog();
          alert(permission);
        }}
      />
    </div>
  );
}
```

```tsx [React Native]
import { Accuracy, Location, startUpdateLocation, StartUpdateLocationPermissionError } from '@apps-in-toss/framework';
import { useCallback, useState } from 'react';
import { Alert, Button, Text, View } from 'react-native';

// 위치 정보 변경 감지하기
function LocationWatcher() {
  const [location, setLocation] = useState<Location | null>(null);

  const handlePress = useCallback(() => {
    startUpdateLocation({
      options: {
        accuracy: Accuracy.Balanced,
        timeInterval: 3000,
        distanceInterval: 10,
      },
      onEvent: (location) => {
        setLocation(location);
      },
      onError: (error) => {
        if (error instanceof StartUpdateLocationPermissionError) {
          // 위치 정보 변경 감지 권한 없음
        }
        console.error('위치 정보를 가져오는데 실패했어요:', error);
      },
    });
  }, []);

  return (
    <View>
      {location != null && (
        <>
          <Text>위도: {location.coords.latitude}</Text>
          <Text>경도: {location.coords.longitude}</Text>
          <Text>위치 정확도: {location.coords.accuracy}m</Text>
          <Text>높이: {location.coords.altitude}m</Text>
          <Text>고도 정확도: {location.coords.altitudeAccuracy}m</Text>
          <Text>방향: {location.coords.heading}°</Text>
        </>
      )}

      <Button title="위치 정보 변경 감지하기" onPress={handlePress} />

      <Button
        title="권한 확인하기"
        onPress={async () => {
          const permission = await startUpdateLocation.getPermission();
          Alert.alert(permission);
        }}
      />
      <Button
        title="권한 요청하기"
        onPress={async () => {
          const permission = await startUpdateLocation.openPermissionDialog();
          Alert.alert(permission);
        }}
      />
    </View>
  );
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-location-callback](https://github.com/toss/apps-in-toss-examples/tree/main/with-location-callback) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
