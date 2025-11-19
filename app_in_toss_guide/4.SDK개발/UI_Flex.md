---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/style-utils/Flex.md
---

# Flex

## Flex

`Flex`는 자식 요소들을 [**Flexbox 레이아웃**](https://reactnative.dev/docs/0.72/flexbox)을 기준으로 배치하는 컴포넌트예요. Flexbox를 사용하면, 가로 및 세로 방향으로 요소들을 쉽게 정렬하고, 중앙 정렬을 간편하게 설정할 수 있어요.
자식 요소를 정 중앙에 배치할 때에는 `Flex.Center`, 세로 중앙에 배치할 때에는 `Flex.CenterVertical`, 가로 중앙에 배치할 때에는 `Flex.CenterHorizontal`을 사용해요.

### 시그니처

```typescript
Flex: FlexType
```

### 파라미터

### 프로퍼티

### 예제

가로, 세로 방향으로 요소들을 배치하는 예제예요.

```tsx
import { Flex } from '@granite-js/react-native';
import { Text } from 'react-native';

function FlexExample() {
  return (
    <>
      <Flex direction="column">
        <Text>세로로 배치해요</Text>
        <Text>1</Text>
        <Text>2</Text>
        <Text>3</Text>
      </Flex>
      <Flex direction="row">
        <Text>가로로 배치해요</Text>
        <Text>1</Text>
        <Text>2</Text>
        <Text>3</Text>
      </Flex>
    </>
  );
}
```

## FlexCenter

`Flex.Center`는 자식 요소들을 [**Flexbox 레이아웃**](https://reactnative.dev/docs/0.72/flexbox) 기준으로 가로와 세로 모두 정 중앙에 배치하는 컴포넌트예요.
`alignItems`와 `justifyContent` 속성 모두 `'center'`로 설정되어, 자식 요소들이 부모 컴포넌트의 중앙에 배치돼요.
`Flexbox`를 사용해 중앙 정렬을 간편하게 할 수 있어요.

### 시그니처

```typescript
FlexCenter: import("react").ForwardRefExoticComponent<Props & import("react").RefAttributes<View>>
```

### 파라미터

### 예제

```tsx
import { Flex } from '@granite-js/react-native';
import { Text } from 'react-native';

function FlexCenterExample() {
  return (
    <Flex.Center style={{ width: '100%', height: 100, borderWidth: 1 }}>
      <Text>정 중앙에 배치해요</Text>
    </Flex.Center>
  );
}
```

## FlexCenterHorizontal

`Flex.CenterHorizontal`는 자식 요소들을 [**Flexbox 레이아웃**](https://reactnative.dev/docs/0.72/flexbox) 기준으로 **가로 방향으로 중앙에 정렬**하기 위한 컴포넌트예요.
`alignItems` 속성이 `'center'`로 설정되어, 자식 요소들이 부모 컴포넌트의 가로 중앙에 배치돼요.

### 시그니처

```typescript
FlexCenterHorizontal: import("react").ForwardRefExoticComponent<Props & import("react").RefAttributes<View>>
```

### 파라미터

### 예제

가로 방향으로 요소들을 중앙 정렬하는 예제예요.

```tsx
import { Flex } from '@granite-js/react-native';
import { Text } from 'react-native';

function FlexCenterHorizontalExample() {
  return (
    <Flex.CenterHorizontal style={{ width: '100%', height: 100, borderWidth: 1 }}>
      <Text>가로 중앙에 배치해요</Text>
    </Flex.CenterHorizontal>
  );
}
```

## FlexCenterVertical

`Flex.CenterVertical`는 자식 요소들을 [**Flexbox 레이아웃**](https://reactnative.dev/docs/0.72/flexbox) 기준으로 **세로 방향으로 중앙에 정렬**하기 위한 컴포넌트예요.
`justifyContent` 속성이 `'center'`로 설정되어, 자식 요소들이 부모 컴포넌트의 세로 중앙에 배치돼요.

### 시그니처

```typescript
FlexCenterVertical: import("react").ForwardRefExoticComponent<Props & import("react").RefAttributes<View>>
```

### 파라미터

### 예제

세로 방향으로 요소들을 중앙 정렬하는 예제예요.

```tsx
import { Flex } from '@granite-js/react-native';
import { Text } from 'react-native';

function FlexCenterVerticalExample() {
  return (
    <Flex.CenterVertical style={{ width: '100%', height: 100, borderWidth: 1 }}>
      <Text>세로 중앙에 배치해요</Text>
    </Flex.CenterVertical>
  );
}
```
