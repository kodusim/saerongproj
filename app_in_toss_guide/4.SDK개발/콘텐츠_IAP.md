---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/인앱
  결제/IAP.md
---

# 인앱 결제

## `IAP`

`IAP`는 인앱 결제 관련 함수를 모아둔 객체예요.

::: tip 주의하세요

토스앱 5.219.0 버전부터 지원해요. 인앱 결제를 지원하지 않는 버전에서는 `undefined`를 반환해요.

:::

### 시그니처

```typescript
IAP {
  getProductItemList: typeof getProductItemList;
  createOneTimePurchaseOrder: typeof createOneTimePurchaseOrder;
  getPendingOrders: typeof getPendingOrders;
  getCompletedOrRefundedOrders: typeof getCompletedOrRefundedOrders;
  completeProductGrant: typeof completeProductGrant;
}
```

### 프로퍼티

## `getProductItemList`

`getProductItemList` 는 인앱 결제로 구매할 수 있는 상품 목록을 담은 함수예요. 상품 목록을 화면에 표시할 때 사용해요.

### 시그니처

```typescript
function getProductItemList(): Promise<{ products: IapProductListItem[] } | undefined>;
```

### 반환값

### 프로퍼티

```typescript
interface IapProductListItem {
  sku: string;
  displayAmount: string;
  displayName: string;
  iconUrl: string;
  description: string;
}
```

### 예제

구매 가능한 인앱결제 상품목록 가져오기

::: code-group

```tsx [React]
import { IAP, IapProductListItem } from "@apps-in-toss/web-framework";
import { Button, List, ListRow } from "@toss/tds-mobile";
import { useEffect, useState } from "react";

function IapProductList() {
  const [products, setProducts] = useState<IapProductListItem[]>([]);

  async function buyIapProduct (productId: string) {
    try {
      await IAP.createOneTimePurchaseOrder({
        productId,
      });

      console.error("인앱결제에 성공했어요");
    } catch (error) {
      console.error("인앱결제에 실패했어요:", error);
    }
  };

  useEffect(() => {
    async function fetchProducts() {
      try {
        const response = await IAP.getProductItemList();
        setProducts(response?.products ?? []);
      } catch (error) {
        console.error("상품 목록을 가져오는 데 실패했어요:", error);
      }
    }

    fetchProducts();
  }, []);

  return (
    <List>
      {products.map((product) => (
        <ListRow
          key={product.sku}
          left={<ListRow.Image type="square" src={product.iconUrl} />}
          contents={
            <ListRow.Texts
              type="3RowTypeA"
              top={product.displayName}
              middle={product.description}
              bottom={product.displayAmount}
            />
          }
          right={
            <Button size="medium" onClick={() => buyIapProduct(product.sku)}>
              구매하기
            </Button>
          }
        />
      ))}
    </List>
  );
}
```

```tsx [React Native]
import { IAP, IapProductListItem } from "@apps-in-toss/framework";
import { Button, List, ListRow } from "@toss/tds-react-native";
import { useEffect, useState } from "react";

function IapProductList() {
  const [products, setProducts] = useState<IapProductListItem[]>([]);

  async function buyIapProduct (productId: string) {
    try {
      await IAP.createOneTimePurchaseOrder({
        productId,
      });

      console.error("인앱결제에 성공했어요");
    } catch (error) {
      console.error("인앱결제에 실패했어요:", error);
    }
  };

  useEffect(() => {
    async function fetchProducts() {
      try {
        const response = await IAP.getProductItemList();
        setProducts(response?.products ?? []);
      } catch (error) {
        console.error("상품 목록을 가져오는 데 실패했어요:", error);
      }
    }

    fetchProducts();
  }, []);

  return (
    <List>
      {products.map((product) => (
        <ListRow
          key={product.sku}
          left={
            <ListRow.Image type="square" source={{ uri: product.iconUrl }} />
          }
          right={
            <Button size="medium" onPress={() => buyIapProduct(product.sku)}>
              구매하기
            </Button>
          }
          contents={
            <ListRow.Texts
              type="3RowTypeA"
              top={product.displayName}
              middle={product.description}
              bottom={product.displayAmount}
            />
          }
        />
      ))}
    </List>
  );
}
```

:::

### 예제 응답

```json
{
  "products": [
    {
      "sku": "sku1",
      "displayName": "광고 제거",
      "displayAmount": "4,900원",
      "iconUrl": "https://cdn.example.com/icons/premium-monthly.png",
      "description": "광고 제거 및 프리미엄 기능 제공"
    },
    {
      "sku": "sku2",
      "displayName": "코인 100개",
      "displayAmount": "9,900원",
      "iconUrl": "https://cdn.example.com/icons/coin-100.png",
      "description": "앱 내에서 사용할 수 있는 코인 100개"
    }
  ]
}
```

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-in-app-purchase](https://github.com/toss/apps-in-toss-examples/tree/main/with-in-app-purchase) 코드를 내려받아 체험해 보세요.

## `createOneTimePurchaseOrder`

`createOneTimePurchaseOrder` 함수는 인앱 결제 결제창을 띄우고, 사용자가 결제를 진행해요. 만약 결제 중에 에러가 발생하면 에러 유형에 따라 에러 페이지로 이동해요.

### 시그니처

```typescript
function createOneTimePurchaseOrder(params: IapCreateOneTimePurchaseOrderOptions): () => void;
```

### 파라미터

```typescript

interface IapCreateOneTimePurchaseOrderOptions {
  options: {sku: string; processProductGrant: (params: { orderId: string }) => boolean | Promise<boolean> };
  onEvent: (event: SuccessEvent) => void | Promise<void>;
  onError: (error: unknown) => void | Promise<void>;
}

interface IapCreateOneTimePurchaseOrderResult {
  orderId: string;
  displayName: string;
  displayAmount: string;
  amount: number;
  currency: string;
  fraction: number;
  miniAppIconUrl: string | null;
}

interface SuccessEvent {
  type: 'success';
  data: IapCreateOneTimePurchaseOrderResult;
}
```

### 에러코드

### 반환값

### 예제

특정 인앱결제 주문서 페이지로 이동하기

::: code-group

```tsx [React]
import { IAP } from "@apps-in-toss/web-framework";
import { Button } from "@toss/tds-mobile";
import { useCallback } from "react";
 
 interface Props {
   sku: string;
 }
 
 function IapCreateOneTimePurchaseOrderButton({ sku }: Props) { 
  const handleClick = useCallback(() => {
    const cleanup = IAP.createOneTimePurchaseOrder({
      options: {
        sku,
        processProductGrant: ({ orderId }) => {
          // 상품 지급 로직을 작성해요.
          return true; // 상품 지급 여부를 반환해요.
        }
        },
      onEvent: (event) => {
        console.log(event);
      },
      onError: (error) => {
        console.error(error);
      },
    });

    return cleanup;
  }, []);

   return <Button onClick={handleClick}>구매하기</Button>;
 }
```

```tsx [React Native]
import { IAP } from "@apps-in-toss/framework";
import { Button } from "@toss/tds-react-native";
import { useCallback } from "react";
 
 interface Props {
   sku: string;
 }
 
 function IapCreateOneTimePurchaseOrderButton({ sku }: Props) {
  const handleClick = useCallback(() => {
    const cleanup = IAP.createOneTimePurchaseOrder({
      options: {
        sku,
        processProductGrant: ({ orderId }) => {
          // 상품 지급 로직을 작성해요.
          return true; // 상품 지급 여부를 반환해요.
        }
        },
      onEvent: (event) => {
        console.log(event);
      },
      onError: (error) => {
        console.error(error);
      },
    });

    return cleanup;
  }, []);

   return <Button onPress={handleClick}>구매하기</Button>;
 }
```

:::

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-in-app-purchase](https://github.com/toss/apps-in-toss-examples/tree/main/with-in-app-purchase) 코드를 내려받아 체험해 보세요.

## `getPendingOrders`

`getPendingOrders` 는 **결제는 완료되었지만 상품이 아직 지급되지 않은 주문 목록**을 가져오는 함수예요.\
조회된 주문 정보를 확인하여 사용자에게 상품을 지급하세요.\
`createOneTimePurchaseOrder` 함수 호출 후 결과를 받지 못한 경우에도 해당 주문을 조회할 수 있어요.

앱 버전이 최소 지원 버전(안드로이드 5.234.0, iOS 5.231.0)보다 낮으면 `undefined`를 반환해요.

### 시그니처

```typescript
function getPendingOrders(): Promise<{ orders: Order[] } | undefined>;
```

### 반환값

### 반환 객체 프로퍼티

```tsx
interface Order {
  orderId: string;
  sku: string;
  paymentCompletedDate?: string;
}
```

::: info 필드 업데이트 안내

* **SDK 1.4.2**: sku 필드가 추가되었어요.
  이 필드는 **안드로이드 5.234.0 이상, iOS 5.231.0 이상**에서만 반환돼요.
* **SDK 1.4.8**: paymentCompletedDate 필드가 추가되었어요.
  결제 완료 시점을 확인할 수 있어요.
  :::

### 예제

::: code-group

```tsx [React]
import { IAP } from '@apps-in-toss/web-framework';
async function fetchOrders() {
  try {
    const pendingOrders = await IAP.getPendingOrders();
    return pendingOrders;
  } catch (error) {
    console.error(error);
  }
}
```

```tsx [ReactNative]
import { IAP } from '@apps-in-toss/framework';
async function fetchOrders() {
 try {
   const pendingOrders = await IAP.getPendingOrders();
   return pendingOrders;
 } catch (error) {
   console.error(error);
 }
}

```

:::

## `completeProductGrant`

`completeProductGrant` 함수는 **대기 중인 주문의 상품 지급을 완료 처리하는 함수**예요.\
사용자에게 상품을 지급하고 `completeProductGrant` 함수를 호출하여 지급 상태를 완료로 변경하세요.

앱 버전이 최소 지원 버전(안드로이드 5.231.0, iOS 5.231.0)보다 낮으면 `undefined`를 반환해요.

### 시그니처

```typescript
function completeProductGrant(params: {
  params: {
    orderId: string;
  };
}): Promise<boolean | undefined>;
```

### 파라미터

### 반환값

### 예제

```tsx [React]
 import { IAP } from '@apps-in-toss/framework';
 
 async function handleGrantProduct(orderId: string) {
   try {
     await IAP.completeProductGrant({ params: { orderId } });
   } catch (error) {
     console.error(error);
   }
 }
```

## `getCompletedOrRefundedOrders`

`getCompletedOrRefundedOrders` 는 인앱결제로 구매하고 환불한 주문 목록을 가져와요.\
인앱결제 결제 및 상품 지급이 완료된 주문건와 환불된 주문건을 조회할 수 있어요.

결제는 완료되었지만 상품이 아직 지급되지 않은 주문건은 조회되지 않아요.\
[`getPendingOrders`](/bedrock/reference/framework/인앱%20결제/getPendingOrders)함수를 통해 `orderId`를 조회하여 사용자에게 상품을 지급한 후 [`completeProductGrant`](/bedrock/reference/framework/인앱%20결제/completeProductGrant)함수를 통해 상품 지급을 완료 처리하세요.

앱 버전이 최소 지원 버전(안드로이드 5.231.0, iOS 5.231.0)보다 낮으면 `undefined`를 반환해요.

### 시그니처

```typescript
function getCompletedOrRefundedOrders(params?: {
  key?: string | null;
}): Promise<CompletedOrRefundedOrdersResult | undefined>;
```

### 반환값

### 반환 객체 프로퍼티

```tsx
interface CompletedOrRefundedOrdersResult {
    hasNext: boolean;
    nextKey?: string | null;
    orders: {
        orderId: string;
        sku: string;
        status: 'COMPLETED' | 'REFUNDED';
        date: string;
    }[];
}
```

### 예제

```tsx [React]
 import { IAP } from '@apps-in-toss/framework';
 
 async function fetchOrders() {
   try {
     const pendingOrders = await IAP.getCompletedOrRefundedOrders();
     return response;
   } catch (error) {
     console.error(error);
   }
 }
```
