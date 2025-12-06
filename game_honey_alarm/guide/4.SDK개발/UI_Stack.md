---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/style-utils/Stack.md
---

# Stack

## Stack

`Stack`은 자식 요소들을 Stack 방식으로 가로 혹은 세로로 배치하고, 자식 요소 사이에 간격을 설정할 수 있는 컴포넌트예요.
`direction` 속성으로 가로(`horizontal`) 또는 세로(`vertical`) 방향을 지정할 수 있고, 자식 요소들 사이의 간격을 `gutter` 속성으로 조절할 수 있어요.
가로로 배치할 때는 `Stack.Horizontal`, 세로로 배치할 때는 `Stack.Vertical` 컴포넌트를 사용할 수 있어요.

### 시그니처

```typescript
Stack: StackType
```

### 파라미터

### 프로퍼티

### 예제

가로, 세로 방향으로 요소들을 배치하고 간격을 16으로 설정한 예제예요.

```tsx
import { Text } from 'react-native';
import { Stack } from '@granite-js/react-native';

function StackExample() {
  return (
    <>
      <Stack gutter={16} direction="horizontal">
        <Text>16간격을 두고 가로 방향으로 배치해요</Text>
        <Text>1</Text>
        <Text>2</Text>
        <Text>3</Text>
      </Stack>
      <Stack gutter={16} direction="vertical">
        <Text>16간격을 두고 세로 방향으로 배치해요</Text>
        <Text>1</Text>
        <Text>2</Text>
        <Text>3</Text>
      </Stack>
    </>
  );
}
```

## StackHorizontal

`Stack.Horizontal`은 자식 요소를 가로로 쌓아 배치하는 컴포넌트에요. 이 컴포넌트를 사용하면, 자식 요소 간의 간격을 `gutter` 속성으로 쉽게 조절할 수 있어, 가로 방향으로 일관된 레이아웃을 유지할 수 있어요.

### 시그니처

```typescript
StackHorizontal: import("react").ForwardRefExoticComponent<StackWithoutDirectionProps & import("react").RefAttributes<View>>
```

### 파라미터

### 예제

가로 방향으로 요소들을 배치하고, 간격을 16으로 설정한 예제예요.

```tsx
import { Stack } from '@granite-js/react-native';
import { View, Text } from 'react-native';

function StackHorizontalExample() {
  return (
       <Stack.Horizontal gutter={16}>
        <Text>16간격을 두고 가로 방향으로 배치해요</Text>
        <Text>1</Text>
        <Text>2</Text>
        <Text>3</Text>
      </Stack.Horizontal>
  );
}
```

## StackVertical

`Stack.Vertical`은 자식 요소를 세로로 쌓아 배치하는 컴포넌트에요. 이 컴포넌트를 사용하면 자식 요소 간의 간격을 `gutter` 속성으로 쉽게 조절할 수 있어, 세로 방향으로 일관된 레이아웃을 유지할 수 있어요.

### 시그니처

```typescript
StackVertical: import("react").ForwardRefExoticComponent<StackWithoutDirectionProps & import("react").RefAttributes<View>>
```

### 파라미터

### 예제

가로 방향으로 요소들을 배치하고 간격으로 16만큼 설정한 예제예요.

```tsx
import { Stack } from '@granite-js/react-native';
import { View, Text } from 'react-native';

function StackVerticalExample() {
  return (
       <Stack.Vertical gutter={16}>
        <Text>16간격을 두고 세로 방향으로 배치해요</Text>
        <Text>1</Text>
        <Text>2</Text>
        <Text>3</Text>
      </Stack.Vertical>
  );
}
```
