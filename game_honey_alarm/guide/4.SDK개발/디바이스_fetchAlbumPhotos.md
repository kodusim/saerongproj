---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/사진/fetchAlbumPhotos.md
---

# 앨범 가져오기

## `fetchAlbumPhotos`

사용자의 앨범에서 사진 목록을 불러오는 함수예요.
최대 개수와 해상도를 설정할 수 있고 갤러리 미리보기, 이미지 선택 기능 등에 활용할 수 있어요.

## 시그니처

```typescript
function fetchAlbumPhotos(options: {
  maxCount: number;
  maxWidth: number;
  base64: boolean;
}): Promise<ImageResponse[]>;
```

### 파라미터

### 프로퍼티

### 반환 값

앨범 사진의 고유 ID와 데이터 URI를 포함한 배열을 반환해요.

## FetchAlbumPhotosPermissionError

사진첩 권한이 거부되었을 때 발생하는 에러예요. 에러가 발생했을 때 `error instanceof FetchAlbumPhotosPermissionError`를 통해 확인할 수 있어요.

## 시그니처

```typescript
class FetchAlbumPhotosPermissionError extends PermissionError {
    constructor();
}
```

## 예제

### 사진의 최대 폭을 360px로 제한하여 가져오기

사진을 가져오는 예제예요.
"권한 확인하기"버튼을 눌러서 현재 사진첩 읽기 권한을 확인해요.
사용자가 권한을 거부했거나 시스템에서 권한이 제한된 경우에는 [`FetchAlbumPhotosPermissionError`](./FetchAlbumPhotosPermissionError)를 반환해요.
"권한 요청하기"버튼을 눌러서 사진첩 읽기 권한을 요청할 수 있어요.

::: code-group

```tsx [React]
import { fetchAlbumPhotos, FetchAlbumPhotosPermissionError, ImageResponse } from '@apps-in-toss/web-framework';
import { useState } from 'react';


const base64 = true;

// 앨범 사진 목록을 가져와 화면에 표시하는 컴포넌트
function AlbumPhotoList() {
  const [albumPhotos, setAlbumPhotos] = useState<ImageResponse[]>([]);

  const handlePress = async () => {
    try {
      const response = await fetchAlbumPhotos({
        base64,
        maxWidth: 360,
      });
      setAlbumPhotos((prev) => [...prev, ...response]);
    } catch (error) {
      if (error instanceof FetchAlbumPhotosPermissionError) {
        // 앨범 읽기 권한 없음
      }
      console.error('앨범을 가져오는 데 실패했어요:', error);
    }
  };

  return (
    <div>
      {albumPhotos.map((image) => {
        // base64 형식으로 반환된 이미지를 표시하려면 데이터 URL 스키마 Prefix를 붙여야해요.
        const imageUri = base64 ? 'data:image/jpeg;base64,' + image.dataUri : image.dataUri;

        return <Image source={{ uri: imageUri }} key={image.id} />;
      })}
      <input type="button" value="앨범 가져오기" onClick={handlePress} />
      <input type="button"
        value="권한 확인하기"
        onClick={async () => {
          const permission = await fetchAlbumPhotos.getPermission();
          alert(permission);
        }}
      />
      <input type="button"
        value="권한 요청하기"
        onClick={async () => {
          const permission = await fetchAlbumPhotos.openPermissionDialog();
          alert(permission);
        }}
      />
    </div>
  );
}
```

```tsx [React Native]
import { fetchAlbumPhotos, FetchAlbumPhotosPermissionError, ImageResponse } from '@apps-in-toss/framework';
import { useState } from 'react';
import { Alert, Button, Image, View } from 'react-native';

const base64 = true;

// 앨범 사진 목록을 가져와 화면에 표시하는 컴포넌트
function AlbumPhotoList() {
  const [albumPhotos, setAlbumPhotos] = useState<ImageResponse[]>([]);

  const handlePress = async () => {
    try {
      const response = await fetchAlbumPhotos({
        base64,
        maxWidth: 360,
      });
      setAlbumPhotos((prev) => [...prev, ...response]);
    } catch (error) {
      if (error instanceof FetchAlbumPhotosPermissionError) {
        // 앨범 읽기 권한 없음
      }
      console.error('앨범을 가져오는 데 실패했어요:', error);
    }
  };

  return (
    <View>
      {albumPhotos.map((image) => {
        // base64 형식으로 반환된 이미지를 표시하려면 데이터 URL 스키마 Prefix를 붙여야해요.
        const imageUri = base64 ? 'data:image/jpeg;base64,' + image.dataUri : image.dataUri;

        return <Image source={{ uri: imageUri }} key={image.id} />;
      })}
      <Button title="앨범 가져오기" onPress={handlePress} />
      <Button
        title="권한 확인하기"
        onPress={async () => {
          const permission = await fetchAlbumPhotos.getPermission();
          Alert.alert(permission);
        }}
      />
      <Button
        title="권한 요청하기"
        onPress={async () => {
          const permission = await fetchAlbumPhotos.openPermissionDialog();
          Alert.alert(permission);
        }}
      />
    </View>
  );
}

```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-album-photos](https://github.com/toss/apps-in-toss-examples/tree/main/with-album-photos) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
