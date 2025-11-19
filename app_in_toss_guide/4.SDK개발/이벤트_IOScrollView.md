---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/IOScrollView.md
---

# 스크롤 영역 노출 감지하기

## `IOScrollView`

`IOScrollView`는 `Intersection Observer` 기능이 추가된 [ScrollView](https://reactnative.dev/docs/scrollview) 컴포넌트예요. 스크롤 중 특정 요소가 화면에 보이거나 사라지는 상태를 감지할 수 있어요.
이 기능을 활용해 `InView` 컴포넌트를 자식 요소로 사용하면, 화면에 노출되는지 여부를 쉽게 확인할 수 있어요.

## 시그니처

```typescript
IOScrollView: ForwardRefExoticComponent<IOScrollViewProps & RefAttributes<IOScrollViewController>>
```

## 예제

`IOScrollView`를 사용해 리스트의 각 항목이 화면에 나타나는지 여부를 확인할 수 있어요.
리스트의 각 항목이 화면에 나타나면 `InView` 컴포넌트가 `visible` 상태로 변경되어요.

```tsx
import { ReactNode, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { InView, IOScrollView } from '@granite-js/react-native';

const mockData = Array.from({ length: 30 }, (_, i) => ({ key: String(i) }));

function IOScrollViewPage() {
 return (
   <IOScrollView>
     {mockData.map((data) => (
       <InViewItem key={data.key}>{data.key}</InViewItem>
     ))}
   </IOScrollView>
 );
}

function InViewItem({ children }: { children: ReactNode }) {
 const [visible, setVisible] = useState(false);

 return (
   <InView onChange={setVisible}>
     <View style={styles.item}>
       <Text>{children}</Text>
       <Text>{visible ? 'visible' : ''}</Text>
     </View>
   </InView>
 );
}

const styles = StyleSheet.create({
 item: {
   padding: 16,
   borderBottomWidth: 1,
   borderBottomColor: '#ddd',
 },
});
```
