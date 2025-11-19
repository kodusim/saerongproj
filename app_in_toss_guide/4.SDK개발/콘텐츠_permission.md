---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/권한/permission.md
---

# 필요한 권한 설정하기

앱에서 클립보드, 위치 정보, 사진첩, 연락처 등의 기능을 사용하려면 권한을 설정해야 해요. 이러한 기능들을 토스앱에서 쓸 수 있도록 권한을 설정하는 방법을 안내해요.

## 권한 목록

아래는 권한 이름과 허용된 작업 목록이에요. 각 권한에 맞는 접근값도 확인해 보세요.

### 클립보드

* 권한 이름: `clipboard`
* 읽기(`read`): [getClipboardText](/bedrock/reference/framework/클립보드/getClipboardText.md)
* 쓰기(`write`): [setClipboardText](/bedrock/reference/framework/클립보드/setClipboardText.md)

### 연락처

* 권한 이름: `contacts`
* 읽기(`read`): [fetchContacts](/bedrock/reference/framework/연락처/fetchContacts.md)

### 사진첩

* 권한 이름: `photos`
* 읽기(`read`): [fetchAlbumPhotos](/bedrock/reference/framework/사진/fetchAlbumPhotos.md)

### 카메라

* 권한 이름: `camera`
* 접근(`access`): [openCamera](/bedrock/reference/framework/카메라/openCamera.md)

### 위치

* 권한 이름: `geolocation`
* 접근(`access`): [startUpdateLocation](/bedrock/reference/framework/위치%20정보/startUpdateLocation.md), [getCurrentLocation](/bedrock/reference/framework/위치%20정보/getCurrentLocation.md), [useGeolocation](/bedrock/reference/framework/위치%20정보/useGeolocation.md)

## 권한 설정하기

앱에서 쓸 권한을 `granite.config.ts`에 정의할 수 있어요. 이는 앱을 검토할 때 쓰여요. [권한 목록](#권한-목록)을 참고해 설정해주세요.

아래는 클립보드와, 카메라, 사진첩을 쓰도록 설정한 예시예요.

::: code-group

```tsx [granite.config.ts]
import { appsInToss } from "@apps-in-toss/framework/plugins";
import { defineConfig } from '@granite-js/react-native/config';

export default defineConfig({
  appName: "<my-service-name>",
  plugins: [
    appsInToss({
      permissions: [
        {
          name: "clipboard",
          access: "read",
        },
        {
          name: "clipboard",
          access: "write",
        },
        {
          name: "camera",
          access: "access",
        },
        {
          name: "photos",
          access: "read",
        },
      ],
    }),
  ],
});
```

:::

## 웹뷰 개발환경에서 설정하기

[웹뷰 개발환경](/tutorials/webview)일 때에도 `granite.config.ts`의 `permissions`에 똑같이 설정하면 돼요.

::: code-group

```tsx [granite.config.ts]
import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "<my-service-name>", // 앱인토스 콘솔에서 설정한 앱 이름
  web: {
    /* 기존설정 */
  },
  permissions: [
    {
      name: "clipboard",
      access: "read",
    },
    {
      name: "clipboard",
      access: "write",
    },
    {
      name: "camera",
      access: "access",
    },
    {
      name: "photos",
      access: "read",
    },
  ],
});
```

:::
