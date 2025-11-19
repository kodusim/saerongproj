---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/인증/tosscertEncrypt.md
---
# 개인정보 암복호화

토스 인증 API는 일부 요청에서 고객의 개인정보가 포함될 수 있어요.  안전을 위해 고객사 서버와 토스 서버는 암호화된 데이터만 주고받아요. 평문이 필요할 땐 데이터를 복호화해 확인해 주세요.

* 인증 요청에서 고객의 이름, 생년월일, 휴대폰번호를 전달할 때 암호화
* 전자서명 서비스 원문에 고객의 개인정보가 포함되는 경우 원문 암호화
* 인증 결과로 토스 서버에서 CI・DI 등을 포함한 개인정보를 제공하는 경우 암호화

:::tip 원터치 본인 인증
고객사 서버에서 토스인증 서버로 고객의 정보를 전달하지 않기 때문에 암호화 과정이 불필요해요.\
다만, 사용자 인증이 완료된 이후 결과조회 API를 호출할 때는 세션키를 포함해서 요청해야 해요.
:::
---

## 세션 키 생성 및 암호화 예제

:::code-group

```java
package im.toss.cert.sdk;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

class TossCertSessionTest {

    @Test
    public void test() {

        // 1. 세션 생성기를 사전에 1회만 생성해 주세요.
        TossCertSessionGenerator tossCertSessionGenerator = new TossCertSessionGenerator();

        // 2. 개인정보가 포함되어 있는 인증요청 API 호출 전에 세션을 생성해 주세요.
        TossCertSession tossCertSession = tossCertSessionGenerator.generate();

        // 3. 개인정보를 암호화 해주세요.
        String userName = "김토스";
        String encryptedUserName = tossCertSession.encrypt(userName);
        System.out.println("encryptedUserName: " + encryptedUserName);

        // 4. 인증요청 API를 호출해 주세요.
        // 인증요청 API의 바디 파라미터에 생성된 sessionKey를 추가해 주세요.
        String sessionKey = tossCertSession.getSessionKey();
        String userName = encryptedUserName;

        // 5. 사용자의 인증이 끝나면 결과조회 API 호출 전에 새로운 세션을 생성해 주세요.
        TossCertSession tossCertSession = tossCertSessionGenerator.generate();

        // 6. 결과조회 API를 호출해주세요.
        // 결과조회 API의 바디 파라미터에 생성된 sessionKey를 추가해 주세요.
        String sessionKey = tossCertSession.getSessionKey();
        String txId = "a39c84d9-458d-47e4-acf7-c481e851f79b";

        // 7. 복호화를 위해 결과조회 요청에서 생성했던 tossCertSession를 가지고 있어야 합니다.
        // response.userName 을 응답받은 암호화된 userName 이라고 가정합니다.
        // decryptedUserName 은 무결성 검증까지 완료되어 있습니다.
        String decryptedUserName = tossCertSession.decrypt(response.userName);
    }
}

```

:::

:::info 참고하세요
토스 테스트 환경에서는 실제 사용자의 개인정보가 아닌 토스가 생성한 가상 인물의 고정된 개인정보를 제공해요.
:::

:::tip 세션키 생성시 사용하는 Public key

```
"MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAoVdxG0Qi9pip46Jw9ImSlPVD8+L2mM47ey6EZna7D7utgNdh8Tzkjrm1Yl4h6kPJrhdWvMIJGS51+6dh041IXcJEoUquNblUEqAUXBYwQM8PdfnS12SjlvZrP4q6whBE7IV1SEIBJP0gSK5/8Iu+uld2ctJiU4p8uswL2bCPGWdvVPltxAg6hfAG/ImRUKPRewQsFhkFvqIDCpO6aeaR10q6wwENZltlJeeRnl02VWSneRmPqqypqCxz0Y+yWCYtsA+ngfZmwRMaFkXcWjaWnvSqqV33OAsrQkvuBHWoEEkvQ0P08+h9Fy2+FhY9TeuukQ2CVFz5YyOhp25QtWyQI+IaDKk+hLxJ1APR0c3tmV0ANEIjO6HhJIdu2KQKtgFppvqSrZp2OKtI8EZgVbWuho50xvlaPGzWoMi9HSCb+8ARamlOpesxHH3O0cTRUnft2Zk1FHQb2Pidb2z5onMEnzP2xpTqAIVQyb6nMac9tof5NFxwR/c4pmci+1n8GFJIFN18j2XGad1mNyio/R8LabqnzNwJC6VPnZJz5/pDUIk9yKNOY0KJe64SRiL0a4SNMohtyj6QlA/3SGxaEXb8UHpophv4G9wN1CgfyUamsRqp8zo5qDxBvlaIlfkqJvYPkltj7/23FHDjPi8q8UkSiAeu7IV5FTfB5KsiN8+sGSMCAwEAAQ==";
```

:::

제공되는 언어를 살펴보세요\
기본적으로 SDK 사용을 권장하지만, 다양한 언어의 코드 샘플도 함께 제공해요
https://github.com/toss/toss-cert-examples
