---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/Image.md
---

# Image

`Image` 컴포넌트를 사용해서 비트맵 이미지(png, jpg 등)나 벡터 이미지(svg)를 로드하고 화면에 렌더링할 수 있어요. 이미지 형식에 맞게 자동으로 적절한 방식으로 렌더링돼요.

## 시그니처

```typescript
function Image(props: ImageProps): import("react/jsx-runtime").JSX.Element;
```

### 파라미터

## 예제

### 이미지 로드 및 렌더링 예시

다음 예시는 비트맵 및 벡터 이미지 리소스를 로드하고, 에러가 발생했을 때 `console.log`로 에러 메시지를 출력하는 방법을 보여줘요.

```tsx
import { View } from 'react-native';
import { Image } from '@granite-js/react-native';

function ImageExample() {
  return (
    <View>
      <Image
        source={{ uri: 'my-image-link' }}
        style={{
          width: 300,
          height: 300,
          borderWidth: 1,
        }}
        onError={() => {
          console.log('이미지 로드 실패');
        }}
      />

      <Image
        source={{ uri: 'my-svg-link' }}
        style={{
          width: 300,
          height: 300,
          borderWidth: 1,
        }}
        onError={() => {
          console.log('이미지 로드 실패');
        }}
      />
    </View>
  );
}
```

### 이미지 불러오기에 실패했을때 처리하기

`Image` 컴포넌트를 사용해서 이미지를 로드하다가 문제가 발생하면, `onError` 콜백이 호출돼요. 이 `onError` 콜백으로 에러를 처리할 수 있어요.

이미지를 불러오다가 네트워크 문제나 잘못된 URL 등으로 인해 이미지를 불러오지 못할 수 있어요.

이때 `onError` 콜백 함수가 호출돼요. 이 콜백을 사용하면 이미지를 불러오는 데 실패했다는 메시지를 콘솔에 출력할 수 있어요.

아래는 에러가 발생했을 때, 빨간색 테두리를 추가한 `View`를 표시하는 코드에요.

`onError` 콜백에서 에러를 감지하고, `hasError` 상태를 업데이트해 에러가 발생했을 때 다른 UI를 보여주는 거죠.

```tsx
import { useState } from "react";
import { View } from "react-native";
import { Image, createRoute } from '@granite-js/react-native';

export const Route = createRoute("/", {
  component: Index,
});

function Index() {
  const [hasError, setHasError] = useState(false); // [!code highlight]

  return (
    <View>
      {hasError === true ? (
        <ErrorView />
      ) : (
        <Image
          style={{
            width: 100,
            height: 100,
          }}
          source={{
            uri: "invalid url", // 잘못된 URL을 사용해서 에러를 발생시켜요. // [!code highlight]
          }}
          onError={() => {
            // [!code highlight:4]
            Alert.alert("이미지 에러");
            setHasError(true);
          }}
        />
      )}
    </View>
  );
}

/** 임의의 에러 뷰 */
function ErrorView() {
  return (
    <View
      style={{
        width: 100,
        height: 100,
        borderColor: "red",
        borderWidth: 1,
      }}
    />
  );
}
```
