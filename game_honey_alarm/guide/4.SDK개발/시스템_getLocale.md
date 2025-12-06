---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/언어/getLocale.md
---

# 로케일 가져오기

## `getLocale`

`getLocale` 함수는 사용자의 로케일(locale) 정보를 반환해요. 네이티브 모듈에서 로케일 정보를 가져올 수 없을 때는 기본값으로 'ko-KR'을 반환합니다. 앱의 현지화 및 언어 설정과 관련된 기능을 구현할 때 사용하세요.

## 시그니처

```typescript
function getLocale(): string;
```

### 반환 값

## 예제

### 현재 사용자의 로케일 정보 가져오기

```tsx
import { getLocale } from '@apps-in-toss/framework';
import { Text } from 'react-native';

function MyPage() {
 const locale = getLocale();

 return (
   <Text>사용자의 로케일 정보: {locale}</Text>
 )
}

```

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-locale](https://github.com/toss/apps-in-toss-examples/tree/main/with-locale) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
