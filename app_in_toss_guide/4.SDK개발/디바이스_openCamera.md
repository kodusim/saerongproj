---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/카메라/openCamera.md
---

# 카메라로 사진 촬영하기

## `openCamera`

카메라를 실행해서 촬영된 이미지를 반환하는 함수예요.

## 시그니처

```typescript
function openCamera(options: {
  base64: boolean;
  maxWidth: number;
}): Promise<ImageResponse>;
```

### 파라미터

### 프로퍼티

### 반환 값

촬영된 이미지 정보를 포함한 객체를 반환해요. 반환 객체의 구성은 다음과 같아요:

* `id`: 이미지의 고유 식별자예요.
* `dataUri`: 이미지 데이터를 표현하는 데이터 URI예요.

## OpenCameraPermissionError

카메라 권한이 거부되었을 때 발생하는 에러예요. 에러가 발생했을 때 `error instanceof OpenCameraPermissionError`를 통해 확인할 수 있어요.

## 시그니처

```typescript
class OpenCameraPermissionError extends PermissionError {
    constructor();
}
```

## 예제

### 카메라 실행 후 촬영된 사진 가져오기

카메라로 사진을 찍고 결과를 가져오는 예제예요.
이 과정에서 현재 카메라 권한 상태를 확인할 수 있고, 권한이 없으면 권한을 요청해요.
사용자가 권한을 거부했거나 시스템에서 권한이 제한된 경우에는 [`OpenCameraPermissionError`](./OpenCameraPermissionError)를 반환해요.

::: code-group

```tsx [React]
import { ImageResponse, openCamera, OpenCameraPermissionError } from '@apps-in-toss/web-framework';
import { useState } from 'react';


const base64 = true;

// 카메라를 실행하고 촬영된 이미지를 화면에 표시하는 컴포넌트
function Camera() {
  const [image, setImage] = useState<ImageResponse | null>(null);

  const handlePress = async () => {
    try {
      const response = await openCamera({ base64 });
      setImage(response);
    } catch (error) {
      if (error instanceof OpenCameraPermissionError) {
        console.log('권한 에러');
      }

      console.error('사진을 가져오는 데 실패했어요:', error);
    }
  };

  // base64 형식으로 반환된 이미지를 표시하려면 데이터 URL 스키마 Prefix를 붙여야해요.
  const imageUri = base64 ? 'data:image/jpeg;base64,' + image?.dataUri : image?.dataUri;

  return (
    <div>
      {image ? <Image source={{ uri: imageUri }} style={{ width: 200, height: 200 }} /> : <span>사진이 없어요</span>}
      <input type="button" value="사진 촬영하기" onClick={handlePress} />
      <input type="button"
        value="권한 확인하기"
        onClick={async () => {
          const permission = await openCamera.getPermission();
          Alert.alert(permission);
        }}
      />

      <input type="button"
        value="권한 요청하기"
        onClick={async () => {
          const currentPermission = await openCamera.openPermissionDialog();
          Alert.alert(currentPermission);
        }}
      />
    </div>
  );
}
```

```tsx [React Native]
import { ImageResponse, openCamera, OpenCameraPermissionError } from '@apps-in-toss/framework';
import { useState } from 'react';
import { Alert, Button, Image, Text, View } from 'react-native';

const base64 = true;

// 카메라를 실행하고 촬영된 이미지를 화면에 표시하는 컴포넌트
function Camera() {
  const [image, setImage] = useState<ImageResponse | null>(null);

  const handlePress = async () => {
    try {
      const response = await openCamera({ base64 });
      setImage(response);
    } catch (error) {
      if (error instanceof OpenCameraPermissionError) {
        console.log('권한 에러');
      }

      console.error('사진을 가져오는 데 실패했어요:', error);
    }
  };

  // base64 형식으로 반환된 이미지를 표시하려면 데이터 URL 스키마 Prefix를 붙여야해요.
  const imageUri = base64 ? 'data:image/jpeg;base64,' + image?.dataUri : image?.dataUri;

  return (
    <View>
      {image ? <Image source={{ uri: imageUri }} style={{ width: 200, height: 200 }} /> : <Text>사진이 없어요</Text>}
      <Button title="사진 촬영하기" onPress={handlePress} />
      <Button
        title="권한 확인하기"
        onPress={async () => {
          const permission = await openCamera.getPermission();
          Alert.alert(permission);
        }}
      />

      <Button
        title="권한 요청하기"
        onPress={async () => {
          const currentPermission = await openCamera.openPermissionDialog();
          Alert.alert(currentPermission);
        }}
      />
    </View>
  );
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-camera](https://github.com/toss/apps-in-toss-examples/tree/main/with-camera) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
