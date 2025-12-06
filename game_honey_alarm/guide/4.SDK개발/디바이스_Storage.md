---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/저장소/Storage.md
---

# 네이티브 저장소 이용하기

## `Storage`

`Storage` 로 네이티브의 저장소를 사용할 수 있어요.

### 시그니처

```typescript
Storage: {
  getItem: typeof getItem;
  setItem: typeof setItem;
  removeItem: typeof removeItem;
  clearItems: typeof clearItems;
}
```

### 프로퍼티

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-storage](https://github.com/toss/apps-in-toss-examples/tree/main/with-storage) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.

## `setItem`

`setItem` 함수는 모바일 앱의 로컬 저장소에 문자열 데이터를 저장해요. 주로 앱이 종료되었다가 다시 시작해도 데이터가 유지되어야 하는 경우에 사용해요.

### 시그니처

```typescript
function setItem(key: string, value: string): Promise<void>;
```

### 파라미터

### 반환 값

### 예제

`my-key`에 아이템 저장하기

::: code-group

```tsx [React]
import { Storage } from '@apps-in-toss/web-framework';
import { Button, Text } from '@toss/tds-mobile';
import { useState } from 'react';

const KEY = 'my-key';

function StorageClearButton() {
  const [storageValue, setStorageValue] = useState<string | null>(null);

  async function handleSet() {
    await Storage.setItem(KEY, 'my-value');
  }

  async function handleGet() {
    const storageValue = await Storage.getItem(KEY);
    setStorageValue(storageValue);
  }

  async function handleRemove() {
    await Storage.removeItem(KEY);
  }

  return (
    <>
      <Text>{storageValue}</Text>
      <Button onClick={handleSet}>저장하기</Button>
      <Button onClick={handleGet}>가져오기</Button>
      <Button onClick={handleRemove}>삭제하기</Button>
    </>
  );
}
```

```tsx [React Native]
import { Storage } from '@apps-in-toss/framework';
import { Button, Text } from '@toss/tds-react-native';
import { useState } from 'react';

const KEY = 'my-key';

function StorageClearButton() {
  const [storageValue, setStorageValue] = useState<string | null>(null);

  async function handleSet() {
    await Storage.setItem(KEY, 'my-value');
  }

  async function handleGet() {
    const storageValue = await Storage.getItem(KEY);
    setStorageValue(storageValue);
  }

  async function handleRemove() {
    await Storage.removeItem(KEY);
  }

  return (
    <>
      <Text>{storageValue}</Text>
      <Button onPress={handleSet}>저장하기</Button>
      <Button onPress={handleGet}>가져오기</Button>
      <Button onPress={handleRemove}>삭제하기</Button>
    </>
  );
}
```

:::

## `getItem`

`getItem` 함수는 모바일 앱의 로컬 저장소에서 문자열 데이터를 가져와요. 주로 앱이 종료되었다가 다시 시작해도 데이터가 유지되어야 하는 경우에 사용해요.

### 시그니처

```typescript
function getItem(key: string): Promise<string | null>;
```

### 파라미터

### 반환 값

### 예제

`my-key`에 저장된 아이템 가져오기

::: code-group

```tsx [React]
import { Storage } from '@apps-in-toss/web-framework';
import { Button, Text } from '@toss/tds-mobile';
import { useState } from 'react';

const KEY = 'my-key';

function StorageClearButton() {
  const [storageValue, setStorageValue] = useState<string | null>(null);

  async function handleSet() {
    await Storage.setItem(KEY, 'my-value');
  }

  async function handleGet() {
    const storageValue = await Storage.getItem(KEY);
    setStorageValue(storageValue);
  }

  async function handleRemove() {
    await Storage.removeItem(KEY);
  }

  return (
    <>
      <Text>{storageValue}</Text>
      <Button onClick={handleSet}>저장하기</Button>
      <Button onClick={handleGet}>가져오기</Button>
      <Button onClick={handleRemove}>삭제하기</Button>
    </>
  );
}
```

```tsx [React Native]
import { Storage } from '@apps-in-toss/framework';
import { Button, Text } from '@toss/tds-react-native';
import { useState } from 'react';

const KEY = 'my-key';

function StorageClearButton() {
  const [storageValue, setStorageValue] = useState<string | null>(null);

  async function handleSet() {
    await Storage.setItem(KEY, 'my-value');
  }

  async function handleGet() {
    const storageValue = await Storage.getItem(KEY);
    setStorageValue(storageValue);
  }

  async function handleRemove() {
    await Storage.removeItem(KEY);
  }

  return (
    <>
      <Text>{storageValue}</Text>
      <Button onPress={handleSet}>저장하기</Button>
      <Button onPress={handleGet}>가져오기</Button>
      <Button onPress={handleRemove}>삭제하기</Button>
    </>
  );
}
```

:::

## `removeItem`

`removeItem` 함수는 모바일 앱의 로컬 저장소에서 특정 키에 해당하는 아이템을 삭제해요.

### 시그니처

```typescript
declare function removeItem(key: string): Promise<void>;
```

### 파라미터

### 반환 값

### 예제

`my-key`에 저장된 아이템 삭제하기

::: code-group

```tsx [React]
import { Storage } from '@apps-in-toss/web-framework';
import { Button, Text } from '@toss/tds-mobile';
import { useState } from 'react';

const KEY = 'my-key';

function StorageClearButton() {
  const [storageValue, setStorageValue] = useState<string | null>(null);

  async function handleSet() {
    await Storage.setItem(KEY, 'my-value');
  }

  async function handleGet() {
    const storageValue = await Storage.getItem(KEY);
    setStorageValue(storageValue);
  }

  async function handleRemove() {
    await Storage.removeItem(KEY);
  }

  return (
    <>
      <Text>{storageValue}</Text>
      <Button onClick={handleSet}>저장하기</Button>
      <Button onClick={handleGet}>가져오기</Button>
      <Button onClick={handleRemove}>삭제하기</Button>
    </>
  );
}
```

```tsx [React Native]
import { Storage } from '@apps-in-toss/framework';
import { Button, Text } from '@toss/tds-react-native';
import { useState } from 'react';

const KEY = 'my-key';

function StorageClearButton() {
  const [storageValue, setStorageValue] = useState<string | null>(null);

  async function handleSet() {
    await Storage.setItem(KEY, 'my-value');
  }

  async function handleGet() {
    const storageValue = await Storage.getItem(KEY);
    setStorageValue(storageValue);
  }

  async function handleRemove() {
    await Storage.removeItem(KEY);
  }

  return (
    <>
      <Text>{storageValue}</Text>
      <Button onPress={handleSet}>저장하기</Button>
      <Button onPress={handleGet}>가져오기</Button>
      <Button onPress={handleRemove}>삭제하기</Button>
    </>
  );
}
```

:::

## `clearItems`

`clearItems` 함수는 모바일 앱의 로컬 저장소의 모든 아이템을 삭제해요.

### 시그니처

```typescript
declare function clearItems(): Promise<void>;
```

### 반환 값

### 예제

저장소 초기화하기

::: code-group

```tsx [React]
import { Storage } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';

function StorageClearButton() {
  async function handleClick() {
    await Storage.clearItems();
    console.log('Storage cleared');
  }

  return <Button onClick={handleClick}>저장소 초기화</Button>;
}
```

```tsx [React Native]
import { Storage } from '@apps-in-toss/framework';
import { Button } from '@toss/tds-react-native';

function StorageClearButton() {
  async function handlePress() {
    await Storage.clearItems();
    console.log('Storage cleared');
  }

  return <Button onPress={handlePress}>저장소 초기화</Button>;
}
```

:::
