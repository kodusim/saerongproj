---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/위치
  정보/Location.md
---

# 위치 정보 객체

## `Location`

`Location` 는 위치 정보를 나타내는 객체예요.

## 시그니처

```typescript
interface Location {
    /**
     * Android에서만 지원하는 옵션이에요.
     *
     * - `FINE`: 정확한 위치
     * - `COARSE`: 대략적인 위치
     *
     * @see https://developer.android.com/codelabs/approximate-location
     */
    accessLocation?: 'FINE' | 'COARSE';
    /**
     * 위치가 업데이트된 시점의 유닉스 타임스탬프예요.
     */
    timestamp: number;
    /**
     * @description 위치 정보를 나타내는 객체예요. 자세한 내용은 [LocationCoords](/react-native/reference/framework/Types/LocationCoords.html)을 참고해주세요.
     */
    coords: LocationCoords;
}
```
