---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/환경
  확인/getSchemeUri.md
---

# 스킴 값 가져오기

## `getSchemeUri`

`getSchemeUri` 는 처음에 화면에 진입한 스킴 값을 반환해요. 페이지 이동으로 인한 URI 변경은 반영되지 않아요.

## 시그니처

```typescript
function getSchemeUri(): string;
```

### 반환 값

## 예제

### 처음 진입한 스킴 값 가져오기

```tsx
import { getSchemeUri } from '@apps-in-toss/framework';
import { Text } from 'react-native';

function MyPage() {
 const schemeUri = getSchemeUri();

 return <Text>처음에 화면에 진입한 스킴 값: {schemeUri}</Text>
}
```
