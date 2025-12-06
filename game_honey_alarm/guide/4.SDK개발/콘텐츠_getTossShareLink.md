---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/공유/getTossShareLink.md
---

# 토스앱 공유 링크 만들기

## `getTossShareLink`

`getTossShareLink` 함수는 사용자가 지정한 경로를 토스 앱에서 열 수 있는 **공유 링크**를 생성해요.\
이 링크를 다른 사람과 공유하면 토스 앱이 실행되며 지정한 경로로 바로 이동해요.

만약 토스앱이 설치되어 있지 않은 경우 :

* iOS 사용자는 **앱스토어**로 이동하고,
* Android 사용자는 **플레이스토어**로 이동해요.

경로는 토스 앱 내부의 특정 화면을 나타내는 **딥링크(deep link)** 형식이어야 해요.\
예를 들어 아래와 같이 작성할 수 있어요.

```
intoss://<앱이름>
intoss://<앱이름>/about?name=test
```

이 함수를 사용하면 `deep_link_value`가 포함된 완성된 공유 링크를 쉽게 만들 수 있어요.

## 앱 출시 전 테스트 방법

`intoss://` 스킴은 **앱이 출시된 이후에만 접근할 수 있어요.**\
앱 출시 전에 테스트를 하려면, 콘솔에 앱 번들을 업로드한 뒤 아래 방법으로 진행하세요.\
([콘솔에서 앱 번들 업로드하기](/development/test/toss.md))

1. 업로드 후 생성된 **QR 코드(앱 스킴)** 를 통해 `deploymentId`를 확인해요.

> `deploymentId`는 앱 번들을 업로드할 때마다 새로 발급돼요.

예시 :

```
intoss-private://intossbench?_deploymentId=0198c10b-68c3-7d2b-a0ab-2c9626b475ec
```

2. 아래 예시를 참고해 테스트를 진행해요.

* 하위 path를 적용한 경우 :

```
intoss-private://intossbench/path/pathpath?_deploymentId=0198c10b-68c3-7d2b-a0ab-2c9626b475ec
```

* 쿼리 파라미터를 적용한 경우 :

```
intoss-private://intossbench?_deploymentId=0198c10b-68c3-7d2b-a0ab-2c9626b475ec&queryParams=%7B%22categoryKey%22%3A%22
```

## 시그니처

```typescript
function getTossShareLink(path: string): Promise<string>;
```

### 파라미터

### 반환 값

## 예제

::: code-group

```tsx [React]
import { share, getTossShareLink } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';

function ShareButton() {
  async function handleClick() {
    // '/' 경로를 딥링크로 포함한 토스 공유 링크를 생성해요.
    const tossLink = await getTossShareLink('intoss://my-app');
    // 생성한 링크를 메시지로 공유해요.
    await share({ message: tossLink });
  }

  return <Button onClick={handleClick}>공유하기</Button>;
}
```

```tsx [React Native]
import { share } from '@apps-in-toss/framework';
import { getTossShareLink } from '@apps-in-toss/framework';
import { Button } from "@toss/tds-react-native";

function ShareButton() {
  async function handleClick() {
    // '/' 경로를 딥링크로 포함한 토스 공유 링크를 생성해요.
    const tossLink = await getTossShareLink('intoss://my-app');
    // 생성한 링크를 메시지로 공유해요.
    await share({ message: tossLink });
  }

  return <Button onClick={handleClick}>공유하기</Button>;
}
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-share-link](https://github.com/toss/apps-in-toss-examples/tree/main/with-share-link) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
