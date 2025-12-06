---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/공유/share.md
---

# 메시지 공유하기

## `share`

`share` 함수로 사용자가 콘텐츠를 쉽게 공유할 수 있도록, 네이티브 공유 시트를 표시할 수 있어요.\
예를 들어, 초대 메시지나 텍스트 정보를 사용자가 설치된 앱 목록에서 원하는 앱(예: 메신저, 메모 앱)을 선택해서 메시지를 공유할 수 있어요. 각 플랫폼(Android, iOS)에서 기본으로 제공하는 공유 인터페이스를 활용해요.

`options.message` 속성에 공유할 메시지를 전달하면, 사용자가 선택할 수 있는 앱 목록이 표시돼요.
예를 들어, 사용자가 텍스트 메시지를 공유하거나 메모 앱에 저장하려고 할 때 유용해요.

## 시그니처

```typescript
function share(message: {
    message: string;
}): Promise<void>;
```

### 파라미터

## 예제

### 공유하기 기능 구현하기

아래는 버튼을 클릭하면 메시지를 공유하는 간단한 예제예요.

::: code-group

```tsx [React]
import { share } from "@apps-in-toss/web-framework";

const ShareButton = () => {
  const handleShare = async () => {
    try {
      await share({ message: "공유할 메시지" });
      console.log("공유 완료");
    } catch (error) {
      console.error("공유 실패:", error);
    }
  };

  return <button onClick={handleShare}>공유하기</button>;
};
```

```tsx [React Native]
import { share } from '@apps-in-toss/framework';
import { Button } from 'react-native';

function MyPage() {
  return (
    <Button
      title="공유"
      onPress={() => share({ message: '공유할 메시지입니다.' })}
    />
  );
}
```

:::

### 사용자 입력을 받아 메시지 공유하기

```tsx
import { useState } from "react";
import { TextInput, Button, View, Alert } from "react-native";
import { share } from '@apps-in-toss/framework';

function ShareWithInput() {
  const [invitationMessage, setInvitationMessage] = useState(""); // [!code highlight]

  const handleShare = () => {
    if (!invitationMessage.trim()) {
      Alert.alert("공유할 메시지를 입력하세요.");
      return;
    }
    share({ message: invitationMessage }); // [!code highlight]
  };

  return (
    <View style={{ padding: 20 }}>
      <TextInput
        style={{
          height: 40,
          borderColor: "gray",
          borderWidth: 1,
          marginBottom: 10,
          paddingHorizontal: 8,
        }}
        placeholder="초대 메시지를 입력하세요"
        value={invitationMessage}
        onChangeText={setInvitationMessage}
      />
      <Button title="초대 메시지 공유" onPress={handleShare} />
    </View>
  );
}
```

### 예제 앱 체험하기

[apps-in-toss-examples](https://github.com/toss/apps-in-toss-examples) 저장소에서 [with-share-text](https://github.com/toss/apps-in-toss-examples/tree/main/with-share-text) 코드를 내려받거나, 아래 QR 코드를 스캔해 직접 체험해 보세요.
