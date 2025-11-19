---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/KeyboardAboveView.md
---

# KeyboardAboveView

키보드가 화면에 나타날 때 자식 컴포넌트를 키보드 위로 자동으로 올려주는 컴포넌트예요.
예를 들어, 텍스트 입력 중 "전송" 버튼을 키보드 위에 고정시키고 싶을 때 유용해요.

## 시그니처

```typescript
function KeyboardAboveView({ style, children, ...props }: ComponentProps<typeof View>): ReactElement;
```

### 파라미터

### 반환 값

## 예제

### 키보드 위로 요소를 올리기

```tsx
import { ScrollView, TextInput, View, Text } from 'react-native';
import { KeyboardAboveView } from '@granite-js/react-native';

function KeyboardAboveViewExample() {
  return (
    <>
      <ScrollView>
        <TextInput placeholder="placeholder" />
      </ScrollView>

      <KeyboardAboveView>
        <View style={{ width: '100%', height: 50, backgroundColor: 'yellow' }}>
          <Text>Keyboard 위에 있어요.</Text>
        </View>
      </KeyboardAboveView>
    </>
  );
}
```
