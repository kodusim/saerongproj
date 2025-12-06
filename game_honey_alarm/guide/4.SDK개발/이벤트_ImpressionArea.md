---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/ImpressionArea.md
---

# 컴포넌트 노출 감지하기

## `ImpressionArea`

`ImpressionArea` 는 특정 컴포넌트가 화면에 보이는지 여부를 감지해서 외부에 알려주는 컴포넌트예요. 이 컴포넌트를 사용해서 화면에 특정 컴포넌트가 보이면 로그를 수집하거나 애니메이션을 실행하는 구현을 쉽게 할 수 있어요.
화면에 보이는지 여부는 `useVisibility`의 반환값과 뷰포트(Viewport) 내에 표시되었는 지 알려주는 `IOScrollView`와 `InView` 컴포넌트로 감지해요. React에서 `ScrollView`를 사용하면 뷰가 화면에 보이지 않더라도, `ImpressionArea`를 사용하면 해당 뷰가 실제로 화면에 보일때만 이벤트를 발생시킬 수 있어요.

::: info 유의하세요

`ImpressionArea`는 반드시 `IOScrollView` 안에서 사용해야 해요. 만약 `IOScrollView` 외부에서 사용해야 한다면, `UNSAFE__impressFallbackOnMount` 속성을 `true`로 설정해서 컴포넌트가 마운트될 때를 기준으로 감지할 수 있어요. 이 속성이 `false`로 설정된 상태에서 `IOScrollView` 외부에서 사용하면 `IOProviderMissingError`가 발생해요.

:::

## 시그니처

```typescript
function ImpressionArea(props: Props): ReactElement;
```

### 파라미터

값은 0부터 1 사이의 숫자로 설정하며, 0으로 설정하면 컴포넌트의 1px이라도 보일 때 이벤트가 발생해요. 반대로, 1로 설정하면 컴포넌트가 100% 화면에 노출될 때만 이벤트가 호출돼요.`IOScrollView`를 사용하지 않는 상황에서, 컴포넌트가 뷰포트(Viewport) 안에 있는지 판단할 수 없을 떼 유용해요. 예를 들어, `IOScrollView` 밖에 위치한 컴포넌트는 `true`로 설정하면 마운트 시점에 보여졌다고 판단해요.

### 반환 값

## 예제

### 기본 사용 예시

```tsx
import { useState } from 'react';
import { Button, Dimensions, Text, View } from 'react-native';
import { ImpressionArea, IOScrollView } from '@granite-js/react-native';

function ImpressionAreaExample() {
 const [isImpressionStart, setIsImpressionStart] = useState(false);

 return (
   <>
     <Text>{isImpressionStart ? 'Impression Start' : 'Impression End'}</Text>
       <IOScrollView
         style={{
           flex: 1,
           margin: 16,
           backgroundColor: 'white',
         }}
       >
       <View
         style={{
           height: Dimensions.get('screen').height,
           borderWidth: 1,
           borderColor: 'black',
         }}
       >
         <Text>Scroll to here</Text>
       </View>

       <ImpressionArea
         onImpressionStart={() => setIsImpressionStart(true)}
         onImpressionEnd={() => setIsImpressionStart(false)}
       >
         <Button title="Button" />
       </ImpressionArea>
     </IOScrollView>
   </>
 );
}
```

### 마운트 시점에 감지하는 예시

`ImpressionArea`가 `IOScrollView`와 같은 컴포넌트 내부에 위치하지 않을 때, `UNSAFE__impressFallbackOnMount`를 `true`로 설정하면 컴포넌트가 마운트될 때 화면에 보여진 것으로 간주해요.

```tsx
import { useState } from 'react';
import { Button, Dimensions, ScrollView, Text, View } from 'react-native';
import { ImpressionArea } from '@granite-js/react-native';

function ImpressionArea2Example() {
 const [isImpressionStart, setIsImpressionStart] = useState(false);

 return (
   <>
     <Text>{isImpressionStart ? 'Impression Start' : 'Impression End'}</Text>
     <ScrollView
       style={{
         flex: 1,
         margin: 16,
         backgroundColor: 'white',
       }}
     >
       <View
         style={{
           height: Dimensions.get('screen').height,
           borderWidth: 1,
           borderColor: 'black',
         }}
       >
         <Text>Scroll to here</Text>
       </View>

       <ImpressionArea
         UNSAFE__impressFallbackOnMount={true}
         onImpressionStart={() => setIsImpressionStart(true)}
         onImpressionEnd={() => setIsImpressionStart(false)}
       >
         <Button title="Button" />
       </ImpressionArea>
     </ScrollView>
   </>
 );
}
```
