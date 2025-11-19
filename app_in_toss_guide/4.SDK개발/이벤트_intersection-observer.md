---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/intersection-observer.md
---

# 스크롤 뷰에서 요소 감지하기

## `IOScrollView`, `ImpressionArea`

[`IOScrollView`](/bedrock/reference/framework/화면%20제어/IOScrollView.md)와 [`ImpressionArea`](/bedrock/reference/framework/화면%20제어/ImpressionArea.md)를 사용해서 스크롤 뷰 내에서 요소가 화면에 보이는지 확인할 수 있어요. 특정 요소가 화면에 일정 비율 이상 나타나면 `onImpressionStart` 콜백이 호출돼요.

[`ImpressionArea`](/bedrock/reference/framework/화면%20제어/ImpressionArea.md)의 `areaThreshold` 값을 설정하면, 설정한 비율 이상으로 요소가 보이면 `onImpressionStart` 콜백이 호출돼요.

::: warning `IOScrollView` 내부에서만 사용할 수 있어요
[`ImpressionArea`](/bedrock/reference/framework/화면%20제어/ImpressionArea.md)는 반드시 [`IOScrollView`](/bedrock/reference/framework/화면%20제어/IOScrollView.md) 내부에 있어야 해요.

그렇지 않으면, `IOContext.Provider 밖에서 사용되었습니다.`라는 에러가 발생해요.
:::

## 스크롤 뷰에서 요소가 20% 이상 나타날 때 처리하기

다음 코드는 높이 `100px`을 가진 요소가 [`IOScrollView`](/bedrock/reference/framework/화면%20제어/IOScrollView.md)에서 `20%`이상 나타났을 때`onImpressionStart`가 호출되는 예제에요.

빨간색 선은 `100px`의 `20%` 지점을 시각적으로 표시한 예시예요.

```tsx{14,18,22-27,37-38}
import { createRoute, ImpressionArea, IOScrollView } from '@granite-js/react-native';
import { ReactNode } from 'react';
import { Alert, Text, View } from 'react-native';

export const Route = createRoute('/image', {
  component: Image,
});

/* 스크롤을 위한 Dummy 콘텐츠 */
const dummies = new Array(10).fill(undefined);

/** 20% 지점 */
const AREA_THRESHOLD = 0.2; // [!code focus]

function Image() {
  return (
    <IOScrollView> // [!code focus]
      {dummies.map((_, index) => {
        return <DummyContent key={index} text={10 - index} />;
      })}
      <ImpressionArea // [!code focus]
        areaThreshold={AREA_THRESHOLD} // [!code focus]
        onImpressionStart={() => { // [!code focus]
          Alert.alert('Impression Start'); // [!code focus]
        }} // [!code focus]
      > // [!code focus]
        <View
          style={{
            width: '100%',
            height: 100,
            backgroundColor: 'blue',
          }}
        >
          <DebugLine areaThreshold={AREA_THRESHOLD} />
        </View>
      </ImpressionArea> // [!code focus]
    </IOScrollView> // [!code focus]
  );
}

/** 비율을 시각적으로 표시하는 디버그 컴포넌트 */
function DebugLine({ areaThreshold }: { areaThreshold: number }) {
  return (
    <View
      style={{
        position: 'absolute',
        top: `${areaThreshold * 100}%`,
        width: '100%',
        height: 1,
        backgroundColor: 'red',
      }}
    />
  );
}

/** Dummy 영역 */
function DummyContent({ text }: { text: ReactNode }) {
  return (
    <View
      style={{
        width: '100%',
        height: 100,
        borderWidth: 1,
      }}
    >
      <Text>{text}</Text>
    </View>
  );
}
```

## 레퍼런스

* [`IOScrollView` 컴포넌트](/bedrock/reference/framework/화면%20제어/IOScrollView.md)
* [`ImpressionArea` 컴포넌트](/bedrock/reference/framework/화면%20제어/ImpressionArea.md)
