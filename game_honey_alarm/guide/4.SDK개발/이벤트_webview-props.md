---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/속성
  제어/webview-props.md
---

# WebView의 속성 제어하기

웹으로 개발한 서비스는 내부적으로 WebView가 사용돼요.

WebView의 설정을 변경하려면 `granite.config.ts` 파일에서 `webViewProps` 속성을 설정하면 돼요. 이를 활용하면 WebView의 동작을 조정하고 사용자 경험을 원하는 방식으로 제어할 수 있어요.

## 사용 가능한 WebView 속성

`webViewProps`에서 설정할 수 있는 주요 속성은 다음과 같아요.

### `allowsInlineMediaPlayback`

HTML5 동영상을 WebView 내에서 전체 화면이 아니라 인라인으로 재생할지 설정해요. iOS 전용 속성이에요. 이 값을 `true`로 설정하고 HTML 문서 내 `<video>` 태그에 `webkit-playsinline` 속성이 있으면 인라인 재생이 가능해요.

* **타입**: `boolean`
* **기본값**: `false`
* **플랫폼**: iOS

### `bounces`

WebView의 스크롤에서 콘텐츠 끝에 도달했을 때 튕기는 효과(바운스 효과)가 발생할지 설정해요. iOS 전용 속성이고, 기본값은 `true`에요.

* **타입**: `boolean`
* **기본값**: `true`
* **플랫폼**: iOS

### `pullToRefreshEnabled`

WebView에서 아래로 당겨서 새로고침하는 기능을 활성화할지 설정해요. iOS 전용 옵션이고, 기본값은 `true`에요. 이 값을 `true`로 설정하면 [`bounces`](#bounces) 옵션도 자동으로 `true`로 설정돼요.

* **타입**: `boolean`
* **기본값**: `true`
* **플랫폼**: iOS

### `overScrollMode`

WebView가 스크롤 콘텐츠 끝에 도달했을 때 Android에서 오버스크롤(over-scroll) 효과를 어떻게 처리할지 설정해요. Android 전용 옵션이고, 기본값은 `always`에요.

* **타입**: `'never'` | `'always'` | `'auto'`
* **기본값**: `'always'`
* **플랫폼**: Android
* **참고 문서**: [Android 공식 문서](https://developer.android.com/reference/android/view/View#OVER_SCROLL_NEVER)

### `mediaPlaybackRequiresUserAction`

오디오나 비디오가 자동으로 재생되지 않도록 설정할 수 있는 값이에요. 이 값을 `true`로 설정하면,\
콘텐츠는 자동으로 재생되지 않고 사용자가 직접 탭해야 재생돼요. 기본값은 `true`예요.

안드로이드에서는 버전 17 이상에서만 이 설정을 적용할 수 있어요.

* **타입**: `boolean`
* **기본값**: `true`
* **플랫폼**: iOS, Android
* **참고 문서**: [react-native-webview mediaPlaybackRequiresUserAction](https://github.com/react-native-webview/react-native-webview/blob/v13.6.2/docs/Reference.md#mediaplaybackrequiresuseraction)

### `allowsBackForwardNavigationGestures`

WebView에서 좌우 스와이프 제스처를 사용해 뒤로 가기 및 앞으로 가기 탐색을 할 수 있게 설정해요. 이 값을 `false`로 설정하면 사용자가 화면을 좌우로 스와이프해서 이전 페이지나 다음 페이지로 탐색할 수 없어요. 기본값은 `true`이고, 스와이프 제스처로 탐색할 수 있어요.

* **타입**: `boolean`
* **기본값**: `true`
* **플랫폼**: iOS
* **참고 문서**: [react-native-webview allowsBackForwardNavigationGestures](https://github.com/react-native-webview/react-native-webview/blob/v13.6.2/docs/Reference.md#allowsBackForwardNavigationGestures)

## 설정 예시

```tsx
import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  // 기타 설정
  webViewProps: {
    bounces: true,
    pullToRefreshEnabled: true,
    allowsInlineMediaPlayback: false,
    overScrollMode: "never",
  },
});
```
