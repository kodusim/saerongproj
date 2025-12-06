---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/화면
  제어/setSecureScreen.md
---

# 화면 캡처 차단하기

## `setSecureScreen`

`setSecureScreen` 함수는 네이티브 수준에서 화면 캡처를 차단하거나 허용할 수 있어요. 사용자가 화면을 캡처하려고 시도할 때 이를 방지해 보안을 강화할 수 있죠. 이 설정은 화면별로 동작하도록 구현할 수 있어 유연하게 사용할 수 있어요.

민감한 정보를 다루는 애플리케이션에서는 화면 캡처를 차단하거나 필요에 따라 허용하는 기능이 중요해요. 이 기능은 특히 금융 앱, 의료 데이터 앱 등 민감한 정보를 보호해야 할 때 유용해요.

예를 들어 계좌 잔고, 거래 내역 같이 민감한 데이터를 표시할 때 활용할 수 있어요.

## 시그니처

```typescript
function setSecureScreen(options: {
    enabled: boolean;
}): Promise<{
    enabled: boolean;
}>;
```

### 파라미터

### 반환 값

## 구현 가이드

### 캡처 차단과 해제 설정하기

아래 코드는 화면이 표시될 때 캡처를 차단하고, 화면을 벗어날 때 차단을 해제해요.

```tsx
import { useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { createRoute } from '@granite-js/react-native';
import { setSecureScreen } from '@apps-in-toss/framework';

export const Route = createRoute("/secure-screen", {
  component: SecureScreen,
});

function SecureScreen() {
  useEffect(() => {
    // 화면에 진입할 때 캡처 차단 활성화
    setSecureScreen({ enabled: true }); // [!code highlight]
    console.log("화면 캡처 차단 활성화");

    return () => {
      // 화면을 벗어날 때 캡처 차단 해제
      setSecureScreen({ enabled: false }); // [!code highlight]
      console.log("화면 캡처 차단 해제");
    };
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.text}>이 화면은 캡처가 차단되어 있습니다.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#f9f9f9",
  },
  text: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#333",
  },
});
```
