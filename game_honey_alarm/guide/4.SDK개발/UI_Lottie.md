---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/Lottie.md
---

# Lottie

`Lottie` 컴포넌트를 사용해서 Lottie 애니메이션을 렌더링할 수 있어요. 이 컴포넌트로 Lottie JSON 파일을 로드하고 애니메이션을 재생해요. 특징으로는 레이아웃 시프팅을 방지하려면 높이를 필수로 지정해야 해요.

## 시그니처

```typescript
function Lottie({ width, maxWidth, height, src, autoPlay, speed, style, onAnimationFailure, ...props }: Props): import("react/jsx-runtime").JSX.Element;
```

### 파라미터

### 반환 값

## 예제

### Lottie 애니메이션 렌더링하기

다음 예시는 Lottie 애니메이션을 렌더링하고, 애니메이션 로드 실패 시 콘솔에 에러 메시지를 출력하는 방법을 보여줘요.

```tsx
import { Lottie } from '@granite-js/react-native';

function LottieExample() {
 return (
   <Lottie
     height={100}
     src="https://my-lottie-animation-url.com"
     autoPlay={true}
     loop={false}
     onAnimationFailure={() => {
       console.log('Animation Failed');
     }}
     onAnimationFinish={() => {
       console.log('Animation Finished');
     }}
   />
 );
```
