---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/광고/GoogleAdMob.md
---

# 인앱 광고 공통 타입·객체

## `GoogleAdMob`

`GoogleAdMob`는 Google AdMob 광고 관련 함수를 모아둔 객체예요.

### 시그니처

```typescript
GoogleAdMob: {
    /**
     * @deprecated 곧 제거될 예정이에요. 대신 `loadAppsInTossAdMob`을 사용해주세요.
     */
    loadAdMobInterstitialAd: typeof loadAdMobInterstitialAd;

    /**
     * @deprecated 곧 제거될 예정이에요. 대신 `showAppsInTossAdMob`을 사용해주세요.
     */
    showAdMobInterstitialAd: typeof showAdMobInterstitialAd;

    /**
     * @deprecated 곧 제거될 예정이에요. 대신 `loadAppsInTossAdMob`을 사용해주세요.
     */
    loadAdMobRewardedAd: typeof loadAdMobRewardedAd;

    /**
     * @deprecated 곧 제거될 예정이에요. 대신 `showAppsInTossAdMob`을 사용해주세요.
     */
    showAdMobRewardedAd: typeof showAdMobRewardedAd;

    loadAppsInTossAdMob: typeof loadAppsInTossAdMob;
    showAppsInTossAdMob: typeof showAppsInTossAdMob;
}
```

### 프로퍼티

## `AdMobFullScreenEvent`

`AdMobFullScreenEvent`는 앱 화면을 덮는 광고(예: 전면 광고, 보상형 광고)를 사용하는 경우에 발생하는 이벤트 타입이에요.

### 시그니처

```typescript
type AdMobFullScreenEvent = AdClicked | AdDismissed | AdFailedToShow | AdImpression | AdShow;
```

### 예제

광고 이벤트 처리하기

```ts
function handleEvent(event: AdMobFullScreenEvent) {
  switch (event.type) {
    case 'clicked':
      console.log('광고가 클릭됐어요.');
      break;

    case 'dismissed':
      console.log('광고가 닫혔어요.');
      break;

    case 'failedToShow':
      console.log('광고가 보여지지 않았어요.');
      break;

    case 'impression':
      console.log('광고가 노출됐어요.');
      break;

    case 'show':
      console.log('광고가 보여졌어요.');
      break;
  }
}
```

## `AdNetworkResponseInfo`

`AdNetworkResponseInfo` 는 광고 네트워크 응답 정보를 담고 있는 객체예요.

### 시그니처

```typescript
interface AdNetworkResponseInfo {
  adSourceId: string;
  adSourceName: string;
  adSourceInstanceId: string;
  adSourceInstanceName: string;
  adNetworkClassName: string | null;
}
```

### 프로퍼티

## `AdNetworkResponseInfo`

`AdNetworkResponseInfo` 는 광고 네트워크 응답 정보를 담고 있는 객체예요.

### 시그니처

```typescript
interface AdNetworkResponseInfo {
  adSourceId: string;
  adSourceName: string;
  adSourceInstanceId: string;
  adSourceInstanceName: string;
  adNetworkClassName: string | null;
}
```

### 프로퍼티
