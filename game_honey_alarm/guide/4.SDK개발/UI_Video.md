---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/Video.md
---

# Video

Video 컴포넌트는 다른 앱에서 음악을 재생 중일 때, 토스 앱에서 그 음악을 중지시키지 않도록 오디오 포커스를 제어하는 로직이 구현된 컴포넌트에요. 앱의 상태에 따라 자동으로 재생하거나 일시정지해요. 예를 들어, 앱이 백그라운드로 전환되면 비디오가 자동으로 일시정지돼요.

::: warning
Video 컴포넌트는 [`react-native-video` 버전(6.0.0-alpha.6)](https://github.com/TheWidlarzGroup/react-native-video/tree/v6.0.0-alpha.6) 을 사용하고 있어요. 따라서 일부 타입이나 기능이 최신 버전과 호환되지 않을 수 있어요.
:::

## 시그니처

```typescript
Video: import("react").ForwardRefExoticComponent<Props & import("react").RefAttributes<VideoRef>>
```

### 파라미터

### 프로퍼티

### 반환 값

## 예제

### 비디오 자동재생 예제

```tsx
import { useRef } from 'react';
import { View } from 'react-native';
import { Video } from '@granite-js/react-native';

function VideoExample() {
  const videoRef = useRef(null);

  return (
    <View>
      <Video
        ref={videoRef}
        source={{ uri: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' }}
        muted={true}
        paused={false}
        resizeMode="cover"
        style={{ width: 300, height: 200, borderWidth: 1 }}
      />
    </View>
  );
}
```

## 참고

* react-native-video https://github.com/react-native-video/react-native-video
  비디오 컴포넌트의 자세한 속성은 공식 문서를 참고해주세요.
* react-native-video-6.0.0-alpha.6 https://github.com/TheWidlarzGroup/react-native-video/releases/tag/v6.0.0-alpha.6
  현재 토스앱에 설치되어있는 버전의 소스코드에요.
