---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/환경
  확인/isMinVersionSupported.md
---

# 앱 최소 버전 확인하기

## `isMinVersionSupported`

`isMinVersionSupported` 함수는 현재 토스 앱 버전이 지정한 최소 버전 이상인지 확인해요.

이 함수는 현재 실행 중인 토스 앱의 버전이 파라미터로 전달된 최소 버전 요구사항을 충족하는지 확인해요. 특정 기능이 최신 버전에서만 동작할 때, 사용자에게 앱 업데이트를 안내할 수 있어요.

## 시그니처

```typescript
function isMinVersionSupported(minVersions: {
  android: `${number}.${number}.${number}` | 'always' | 'never';
  ios: `${number}.${number}.${number}` | 'always' | 'never';
}): boolean;
```

### 파라미터

### 반환 값

## 예제

### 앱 버전 확인하기

::: code-group

```tsx [React]
import { isMinVersionSupported } from '@apps-in-toss/web-framework';
import { Text } from '@toss/tds-mobile';

function VersionCheck() {
  const isSupported = isMinVersionSupported({
    android: '1.2.0',
    ios: '1.3.0',
  });

  return <div>{!isSupported && <Text>최신 버전으로 업데이트가 필요해요.</Text>}</div>;
}
```

```tsx [React Native]
import { isMinVersionSupported } from '@apps-in-toss/framework';
import { Text } from '@toss/tds-react-native';
import { View } from 'react-native';

function VersionCheck() {
  const isSupported = isMinVersionSupported({
    android: '1.2.0',
    ios: '1.3.0'
  });

  return (
    <View>
      {!isSupported && (
        <Text>최신 버전으로 업데이트가 필요해요.</Text>
      )}
    </View>
  );
}
```

:::
