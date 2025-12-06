---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/위치
  정보/Accuracy.md
---

# 정확도 옵션

## `Accuracy`

`Accuracy` 는 위치 정확도 옵션이에요.

## 시그니처

```typescript
enum Accuracy {
    /**
     * 오차범위 3KM 이내
     */
    Lowest = 1,
    /**
     * 오차범위 1KM 이내
     */
    Low = 2,
    /**
     * 오차범위 몇 백미터 이내
     */
    Balanced = 3,
    /**
     * 오차범위 10M 이내
     */
    High = 4,
    /**
     * 가장 높은 정확도
     */
    Highest = 5,
    /**
     * 네비게이션을 위한 최고 정확도
     */
    BestForNavigation = 6
}
```
