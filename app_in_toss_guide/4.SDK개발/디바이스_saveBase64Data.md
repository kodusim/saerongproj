---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/데이터/saveBase64Data.md
---

# 파일 저장하기

## `saveBase64Data`

`saveBase64Data` 함수는 문자열로 인코딩된 Base64 데이터를 지정한 파일 이름과 MIME 타입으로 사용자 기기에 저장해요. 이미지, 텍스트, PDF 등 다양한 형식의 데이터를 저장할 수 있어요.

## 시그니처

```typescript
function saveBase64Data(params: SaveBase64DataParams): Promise<void>;
```

### 파라미터

## 예제

### Base64 이미지 데이터를 사용자 기기에 저장하기

::: code-group

```tsx [React]
import { saveBase64Data } from '@apps-in-toss/web-framework';
import { Button } from '@toss/tds-mobile';

function SaveButton() {
  const handleSave = async () => {
    try {
      await saveBase64Data({
        data: 'iVBORw0KGgo...',
        fileName: 'some-photo.png',
        mimeType: 'image/png',
      });
    } catch (error) {
      console.error('데이터 저장에 실패했어요:', error);
    }
  };

  return <Button onClick={handleSave}>저장</Button>;
}
```

```tsx [React Native]
import { saveBase64Data } from '@apps-in-toss/framework';
import { Button } from "@toss/tds-react-native";

function SaveButton() {
  const handleSave = async () => {
    try {
      await saveBase64Data({
        data: 'iVBORw0KGgo...',
        fileName: 'some-photo.png',
        mimeType: 'image/png',
      });
    } catch (error) {
      console.error('데이터 저장에 실패했어요:', error);
    }
  };

  return <Button onPress={handleSave}>저장</Button>;
}
```

:::
