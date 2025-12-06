---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/style-utils/margin.md
---

# margin

`margin` 함수는 컴포넌트의 외부 간격을 설정해서, 컴포넌트들 간의 적절한 간격을 확보해요. 가로(x), 세로(y), 그리고 각 방향(top, right, bottom, left)별로 외부 여백을 숫자로 지정할 수 있어요.
숫자를 입력하면 모든 방향에 동일한 값을 적용하거나, 각 방향별로 개별 설정이 가능해요. 또한 자주 쓰는 값에 대한 프리셋이 있어 쉽게 적용할 수 있어요.

## 시그니처

```typescript
margin: BoxSpacing
```

### 파라미터

각 방향에 대해 개별 값을 설정할 수도 있어요.

### 프로퍼티

## 예제

## 가로, 세로 방향에 8px의 바깥쪽 여백을 적용하고, 아래 방향에 임의의 여백(100px)을 적용하는 예제예요.

```tsx
import { padding } from '@granite-js/react-native';
import { View } from 'react-native';

function Component() {
  return (
    <View>
      <View style={margin.x8}>
        <Text>가로 여백이 있어요</Text>
      </View>
      <View style={margin.y8}>
        <Text>세로 여백이 있어요</Text>
      </View>
      <View style={margin.bottom(100)}>
        <Text>아래에 100만큼의 여백이 있어요</Text>
      </View>
    </View>
  );
}
```
