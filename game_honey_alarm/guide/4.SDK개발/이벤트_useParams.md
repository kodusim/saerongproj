---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/useParams.md
---

# 쿼리 파라미터 사용하기

## `useParams`

`useParams`는 지정된 라우트에서 파라미터를 가져오는 훅이에요.

애플리케이션이 [URL 스킴](https://en.wikipedia.org/wiki/Uniform_Resource_Identifier)으로 실행될 때, 스킴에 포함된 [쿼리 스트링](https://en.wikipedia.org/wiki/Query_string) 값을 참조할 수 있어요. 스킴으로 애플리케이션을 실행할 때, 필요한 데이터를 전달하거나 특정 기능을 활성화할 수 있어요.

추가로 `validateParams` 옵션을 활용하면, 화면에서 필요한 쿼리 파라미터를 정의하고 유효성을 검사할 수 있어요.

## 시그니처

```typescript
function useParams<TScreen extends keyof RegisterScreen>(options: {
    from: TScreen;
    strict?: true;
}): RegisterScreen[TScreen];
```

### 파라미터

## 예제

### 라우트 파라미터 가져오기

::: code-group

```tsx [React Native]
import React from 'react';
import { Text } from 'react-native';
import { createRoute, useParams } from '@granite-js/react-native';

export const Route = createRoute('/examples/use-params', {
  validateParams: (params) => params as { id: string },
  component: UseParamsExample,
});

function UseParamsExample() {
  // 첫 번째 방법: 라우트 객체의 `useParams` 메서드 사용
  const params = Route.useParams();

  // 두 번째 방법: useParams 훅 직접 사용
  const params2 = useParams({ from: '/examples/use-params' });

  // 세 번째 방법: strict 모드를 false로 설정하여 사용
  // strict: false로 설정하면 현재 라우트의 파라미터를 가져오며,
  // validateParams가 정의되어 있어도 검증을 건너뛰어요.
  const params3 = useParams({ strict: false }) as { id: string };

  return (
    <>
      <Text>{params.id}</Text>
      <Text>{params2.id}</Text>
      <Text>{params3.id}</Text>
    </>
  );
}
```

:::

## 쿼리 스트링 값 유효성 검증하기

필수로 포함해야 하는 쿼리 파라미터는 `validateParams` 옵션을 사용해서 유효성을 검사할 수 있어요.

예를 들어, 아래 예시 코드는 `name` 파라미터가 없으면 에러를 발생시켜요.

그래서 필수 쿼리 파라미터가 누락되지 않도록 `validateParams` 옵션을 사용해요.

::: code-group

```tsx [vanilla]
import { createRoute } from '@granite-js/react-native';
import { View, Text } from "react-native";

export const Route = createRoute("/", {
  component: Index,
  validateParams: (params) => {
    if (!("name" in params)) {
      throw Error("name is required");
    }
    if (typeof params.name !== "string") {
      throw Error("name must be a string");
    }

    if (!("age" in params)) {
      throw Error("age is required");
    }
    if (typeof params.age !== "number") {
      throw Error("age must be a number");
    }

    return params as {
      name: string;
      age: number;
    };
  },
});

function Index() {
  const { name, age } = Route.useParams();

  return (
    <View>
      <Text>이름: {name}</Text>
      <Text>나이: {age}</Text>
    </View>
  );
}
```

```tsx [valibot]
import { createRoute } from '@granite-js/react-native';
import { View, Text } from "react-native";
import * as v from "valibot";

export const Route = createRoute("/", {
  component: Index,
  validateParams: (params) => {
    return v.parse(
      v.object({
        name: v.string(),
        age: v.number(),
      }),
      params
    );
  },
});

function Index() {
  const { name, age } = Route.useParams();

  return (
    <View>
      <Text>이름: {name}</Text>
      <Text>나이: {age}</Text>
    </View>
  );
}
```

```tsx [zod]
import { createRoute } from '@granite-js/react-native';
import { View, Text } from "react-native";
import { z } from "zod";

export const Route = createRoute("/", {
  component: Index,
  validateParams: (params) => {
    return z
      .object({
        name: z.string(),
        age: z.number(),
      })
      .parse(params);
  },
});

function Index() {
  const { name, age } = Route.useParams();

  return (
    <View>
      <Text>이름: {name}</Text>
      <Text>나이: {age}</Text>
    </View>
  );
}
```

:::

## 쿼리 파라미터 값 변환하기

`createRoute.parserParams` 옵션을 사용하면 쿼리 스트링으로 전달된 `string` 값을 원하는 타입으로 변환할 수 있어요.\
기본적으로 `useParams`는 숫자, 문자열, 배열, 객체 같은 대부분의 단순 타입은 자동으로 변환하기 때문에 파서를 직접 재정의해야 할 일은 많지 않아요.\
하지만 복잡한 데이터 구조를 사용해야 할 때나 특정한 params를 지우고 싶을 때는 파서를 직접 정의해서 원하는 타입으로 변환할 수 있어요.

`parserParams` 옵션의 결과가 `validateParams` 옵션에 전달되기 전에 변환됩니다.

### 기본 파서를 사용한 타입 변환

기본 파서를 활용하면 쿼리 스트링 값이 자동으로 적절한 타입으로 변환돼요. 아래 예제는 쿼리 파라미터를 타입에 맞게 변환하는 방법을 보여줘요.

```tsx
import { createRoute } from '@granite-js/react-native';
import { View, Text } from "react-native";

// URL 예시: intoss://test-app?name=tom&age=10&arr=1,2,3&obj={"name":"jane","age":20}
export const Route = createRoute("/", {
  component: Index,
  validateParams: (params) => ({
    // 기본 파서로 인해 쿼리 파라미터 값을 올바른 타입으로 자동으로 변환
    name: params.name as string, // 문자열로 변환
    age: params.age as number, // 숫자로 변환
    arr: params.arr as string[], // 배열로 변환
    obj: params.obj as { name: string; age: number }, // 객체로 변환
  }),
});

function Index() {
  const { name, age, arr, obj } = Route.useParams();

  return (
    <View>
      <Text>
        이름: {name}, 타입: {typeof name}
      </Text>
      <Text>
        나이: {age}, 타입: {typeof age}
      </Text>
      <Text>
        배열: {JSON.stringify(arr)}, 타입: {typeof arr}
      </Text>
      <Text>
        객체: {JSON.stringify(obj)}, 타입: {typeof obj}
      </Text>
    </View>
  );
}
```

### 파서 재정의

`parserParams` 옵션을 사용하면 기본 파서로 처리하기 어려운 query parameter를 변환하는 함수를 직접 정의해서 사용할 수 있어요. 예를 들어, 특정 파라미터(`referer`)를 제거하고 나머지 파라미터를 기본 파서로 처리하는 방법을 아래 코드에서 보여줘요.

```tsx
import { createRoute } from '@granite-js/react-native';
import { View, Text } from "react-native";

// URL 예시: intoss://test-app?name=tom&age=10&referer=https://google.com
export const Route = createRoute("/", {
  component: Index,

  // 특정 파라미터를 제거하고 나머지를 기본 파서로 처리 // [!code highlight:5]
  parserParams: (params) => {
    const { referer, ...rest } = params;
    return rest;
  },

  validateParams: (params) => {
    // [!code highlight:11]
    // 여기서 `params`는 parserParams 함수에서 변환된 값이에요.
    // 즉, `referer`는 이미 제거된 상태로 전달돼요.
    return {
      name: params.name,
      age: params.age,
    } as {
      name: string;
      age: number;
    };
  },
});

// 컴포넌트에서 파라미터 사용
function Index() {
  const { name, age } = Route.useParams();

  return (
    <View>
      <Text>
        이름: {name}, 타입: {typeof name}
      </Text>
      <Text>
        나이: {age}, 타입: {typeof age}
      </Text>
    </View>
  );
}
```

::: warning 중복된 쿼리 파라미터 주의사항
만약 같은 이름의 쿼리 파라미터가 여러 번 사용되면, 해당 값은 배열로 반환돼요. 예를 들어, `age` 파라미터가 두 번 포함되면 다음과 같이 처리돼요.

```js
// 스킴: `intoss://test-app?name=tom&age=10&age=20`
const params = useParams({
  from: "/",
});

// params
{ name: 'tom', age: [10, 20] }
```

:::

***

::: warning 이전 버전 문서가 필요할 때
이전 버전의 문서는 [쿼리 파라미터 사용하기](/learn-more/query-parameter-deprecated)에서 확인할 수 있어요.
:::
