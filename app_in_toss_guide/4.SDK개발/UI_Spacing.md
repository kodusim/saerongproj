---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/style-utils/Spacing.md
---

# Spacing

`Spacing`은 빈 공간을 차지해서 여백을 추가하는 컴포넌트예요. 가로 혹은 세로 방향으로 여백의 크기를 지정할 수 있어요.

## 시그니처

```typescript
Spacing: import("react").NamedExoticComponent<Props>
```

### 파라미터

## 예제

### 가로, 세로 방향에 크기가 `16`인 여백을 추가하여 빈 공간을 만들어 낸 예제

```tsx
import { View, Text } from 'react-native';
import { Spacing } from '@granite-js/react-native';

function SpacingExample() {
  return (
    <View>
      <Text>Top</Text>
      <Spacing size={16} direction="vertical" style={{ backgroundColor: 'red', width: 5 }} />
      <Text>Bottom, 세로 여백만큼 아래에 위치해 있어요</Text>

      <View style={{ flexDirection: 'row' }}>
        <Text>Left</Text>
        <Spacing size={16} direction="horizontal" style={{ backgroundColor: 'red', height: 5 }} />
        <Text>Right, 가로 여백만큼 옆에 위치해 있어요</Text>
      </View>
    </View>
  );
}
```
