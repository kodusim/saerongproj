---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/위치
  정보/LocationCoords.md
---

# 좌표 정보

## `LocationCoords`

`LocationCoords`는 세부 위치 정보를 나타내는 객체예요.

## 시그니처

```typescript
interface LocationCoords {
    /**
     * 위도
     */
    latitude: number;
    /**
     * 경도
     */
    longitude: number;
    /**
     * 높이
     */
    altitude: number;
    /**
     * 위치 정확도
     */
    accuracy: number;
    /**
     * 고도 정확도
     */
    altitudeAccuracy: number;
    /**
     * 방향
     */
    heading: number;
}
```
