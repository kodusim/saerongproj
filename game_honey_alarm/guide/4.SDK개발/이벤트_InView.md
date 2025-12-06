---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/InView.md
---

# 요소 노출 감지하기

## `InView`

`InView` 컴포넌트는 화면에 요소가 보이기 시작하거나 화면에서 사라지는 것을 감지하는 컴포넌트예요.
요소가 화면에 조금이라도 보이기 시작하면 `onChanged` 핸들러가 호출되고 첫 번째 인자로 `true` 값이 전달돼요. 반대로 요소가 화면에서 사라지면 `false` 값이 전달돼요.
`onChanged` 핸들러의 두 번째 인자로 요소의 화면 노출 비율이 전달돼요. 노출 비율 값은 `0`에서 `1.0` 사이예요. 예를 들어 `0.2`가 전달되면 컴포넌트가 20%만큼 화면에 노출된 상태라는 의미예요.

::: warning 유의하세요

`InView`는 반드시 `IOContext`가 포함된 [IOScrollView](/bedrock/reference/framework/화면%20제어/IOScrollView) 또는 [IOFlatList](/bedrock/reference/framework/화면%20제어/IOFlatList) 내부에서 사용해야 해요.
만약 `IOContext` 외부에서 사용하면 `IOProviderMissingError`가 발생해요.

:::

## 시그니처

```typescript
class InView<T = ViewProps> extends PureComponent<InViewProps<T>> {
  static contextType: import("react").Context<IOContextValue>;
  static defaultProps: Partial<InViewProps>;
  context: undefined | IOContextValue;
  mounted: boolean;
  protected element: Element;
  protected instance: undefined | ObserverInstance;
  protected view: any;
  constructor(props: InViewProps<T>);
  componentDidMount(): void;
  componentWillUnmount(): void;
  protected handleChange: (inView: boolean, areaThreshold: number) => void;
  protected handleRef: (ref: any) => void;
  protected handleLayout: (event: LayoutChangeEvent) => void;
  measure: (...args: any) => void;
  measureInWindow: (...args: any) => void;
  measureLayout: (...args: any) => void;
  setNativeProps: (...args: any) => void;
  focus: (...args: any) => void;
  blur: (...args: any) => void;
  render(): import("react/jsx-runtime").JSX.Element | null;
}
```

### 파라미터

## 예제

### `InView`컴포넌트로 요소의 `10%` 지점을 감지하기

```tsx
import { LayoutChangeEvent, View, Text, Dimensions } from "react-native";
import { InView, IOScrollView } from '@granite-js/react-native';

function InViewExample() {
  const handleLayout = (event: LayoutChangeEvent) => {
    console.log("레이아웃 변경됨", event.nativeEvent.layout);
  };

  const handleChange = (inView: boolean, areaThreshold: number) => {
    if (inView) {
      console.log(`${areaThreshold * 100}% 비율만큼 화면에 보이는 상태`);
    } else {
      console.log("화면에 보이지 않는 상태");
    }
  };

  return (
    <IOScrollView>
      <View style={{ height: HEIGHT, width: "100%", backgroundColor: "blue" }}>
        <Text style={{ color: "white" }}>스크롤을 내려주세요</Text>
      </View>
      <InView onLayout={handleLayout} onChange={handleChange}>
        <View style={{ width: 100, height: 300, backgroundColor: "yellow" }}>
          <View
            style={{
              position: "absolute",
              top: 30,
              width: 100,
              height: 1,
              borderWidth: 1,
            }}
          >
            <Text style={{ position: "absolute", top: 0 }}>10% 지점</Text>
          </View>
        </View>
      </InView>
    </IOScrollView>
  );
}
```
