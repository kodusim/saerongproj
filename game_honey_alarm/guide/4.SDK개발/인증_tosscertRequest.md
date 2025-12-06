---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/인증/tosscertRequest.md
---

# 인증 화면 호출

본인확인 요청 API 응답에서 받은 `txId`를 포함해 `appsInTossSignTossCert`를 호출해요.

::: info 원터치 인증 및 앱 버전 안내
**원터치 인증 방식(`USER_NONE`)** 을 사용하는 경우,\
`skipConfirmDoc`을 `true`로 설정하면 인증서 확인 문서 단계를 건너뛸 수 있어요.

* 토스 인증(requestType: USER\_PERSONAL): 토스앱 5.233.0 이상
* 토스 원터치 인증(requestType: USER\_NONE): 토스앱 5.236.0 이상

[getTossAppVersion](/bedrock/reference/framework/환경%20확인/getTossAppVersion) 함수를 사용하여 토스앱 버전을 체크해보세요.
:::

:::code-group

```tsx [React]
import { appsInTossSignTossCert } from '@apps-in-toss/web-framework';

interface AppsInTossSignTossCertParams {
  txId: string; // 본인확인 요청 시 발급받은 txId
  skipConfirmDoc?: boolean; // 원터치 인증 시 true로 설정
}

/**
 * Toss 인증서 화면을 txId 기반으로 호출합니다.
 *
 * 참고:
 * response는 인증 완료 확정 용도가 아닙니다.
 * 서버에서 txId 기준으로 결과조회 API를 호출해 최종 상태를 판별하세요.
 */
export async function openTossCertWithTxId(
  txId: string,
  skipConfirmDoc = false
): Promise<unknown> {
  try {
    const params: AppsInTossSignTossCertParams = { txId, skipConfirmDoc };
    const response = await appsInTossSignTossCert(params);
    return response;
  } catch (e: unknown) {
    // 호출 실패 처리 (사용자 취소/앱 미설치/스킴 실패 등)
    throw e;
  }
}

```

```tsx [ReactNative]
import { appsInTossSignTossCert } from '@apps-in-toss/framework';

interface AppsInTossSignTossCertParams {
  txId: string; // 본인확인 요청 시 발급받은 txId
  skipConfirmDoc?: boolean; // 원터치 인증 시 true로 설정
}

/**
 * Toss 인증서 화면을 txId 기반으로 호출합니다.
 *
 * 참고:
 * response는 인증 완료 확정 용도가 아닙니다.
 * 서버에서 txId 기준으로 결과조회 API를 호출해 최종 상태를 판별하세요.
 */
export async function openTossCertWithTxId(
  txId: string,
  skipConfirmDoc = false
): Promise<unknown> {
  try {
    const params: AppsInTossSignTossCertParams = { txId, skipConfirmDoc };
    const response = await appsInTossSignTossCert(params);
    return response;
  } catch (e: unknown) {
    // 호출 실패 처리 (사용자 취소/앱 미설치/스킴 실패 등)
    throw e;
  }
}

```

## :::

### 응답

* `onSuccess`
  * 파라미터 없음
* `onError`
  * `Error { code: string; message: string }` (예: 사용자 취소, 앱 미설치, 스킴 실패 등)

```ts
// 에러 타입 예시
type AppsInTossSignTossCertError = {
  code: string;
  message: string;
};

// try/catch로 onSuccess/onError 대응하기
try {
  await appsInTossSignTossCert({
    params: {
      txId: "bb8bead6-0957-4be7-b937-f554911d7a87",
      skipConfirmDoc: true, // 원터치 인증 시 설정
    },
  });
  // onSuccess: 파라미터 없음
} catch (e: any) {
  const err: AppsInTossSignTossCertError = {
    code: e?.code ?? 'UNKNOWN',
    message: e?.message ?? String(e),
  };
  // onError: 에러 처리
}
```
