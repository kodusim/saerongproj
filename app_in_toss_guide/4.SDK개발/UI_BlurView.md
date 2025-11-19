---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/BlurView.md
---

# BlurView

`BlurView` 컴포넌트는 iOS에서 배경을 블러 처리하는 UI 효과를 줘요. 이 컴포넌트는 배경을 흐리게 표시해요. iOS에서만 지원되고
Android에서는 기본 [`View`](https://reactnative.dev/docs/0.72/view) 를 렌더링해요.

블러의 강도를 조절할 수 있고, [Vibrancy 효과](https://developer.apple.com/documentation/uikit/uivibrancyeffect?language=objc)를 적용할 수 있어요. 블러가 적용되지 않을 경우에는 [`reducedTransparencyFallbackColor`](https://github.com/Kureev/react-native-blur/tree/v4.3.2?tab=readme-ov-file#blurview)를 사용해 배경색을 설정할 수 있어요.

`isSupported` 속성을 통해 현재 기기에서 블러가 지원되는지 확인할 수 있어요. iOS 5.126.0 이상에서만 블러 효과가 지원되고, Android에서는 지원되지 않아요.

## 시그니처

```typescript
function BlurView({ blurType, blurAmount, reducedTransparencyFallbackColor, vibrancyEffect, ...viewProps }: BlurViewProps): import("react/jsx-runtime").JSX.Element;
```

### 파라미터

### 반환 값

::: warning 유의할 점
`BlurView`는 iOS에서만 지원돼요. Android에서는 기본 `View`가 렌더링되며, 블러 효과가 적용되지 않아요.
:::

## 예제

### `BlurView`를 사용해 텍스트를 블러 처리하기

```tsx
import { View, Text, StyleSheet } from 'react-native';
import { BlurView } from '@granite-js/react-native';

function BlurViewExample() {
 return (
   <View style={styles.container}>
     <Text style={styles.absolute}>Blurred Text</Text>
     <BlurView style={styles.absolute} blurType="light" blurAmount={1} />
     <Text>Non Blurred Text</Text>
   </View>
 );
}

const styles = StyleSheet.create({
 container: {
   justifyContent: 'center',
   alignItems: 'center',
   width: '100%',
   height: 300,
 },
 absolute: {
   position: 'absolute',
   top: 0,
   left: 0,
   bottom: 0,
   right: 0,
 },
});
```

## 참고

* [iOS Vibrancy Effect Documentation](https://developer.apple.com/documentation/uikit/uivibrancyeffect)
* [Zeddios Blog 설명](https://zeddios.tistory.com/1140)
