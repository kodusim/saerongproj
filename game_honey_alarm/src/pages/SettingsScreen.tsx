import { useAuth } from '../hooks/useAuth';
import { useQuery } from '@tanstack/react-query';
import { subscriptionAPI, testAPI } from '../api/services';
import { useState } from 'react';

export default function SettingsScreen() {
  const { user } = useAuth();
  const [sendingPush, setSendingPush] = useState(false);

  // 내 구독 목록 조회
  const { data: subscriptions = [], isLoading: subsLoading } = useQuery({
    queryKey: ['mySubscriptions'],
    queryFn: subscriptionAPI.getMySubscriptions,
    enabled: !!user,
  });

  // 프리미엄 구독 상태 조회
  const { data: premiumStatus } = useQuery({
    queryKey: ['premiumStatus'],
    queryFn: subscriptionAPI.getPremiumStatus,
    enabled: !!user,
  });

  return (
    <div style={{
      padding: '0',
      paddingBottom: '80px',
      minHeight: '100vh',
      backgroundColor: '#F8F9FA'
    }}>
      {/* 헤더 */}
      <div style={{
        padding: '20px 24px',
        backgroundColor: 'white',
        borderBottom: '1px solid #E5E8EB'
      }}>
        <h1 style={{
          fontSize: '24px',
          fontWeight: 'bold',
          margin: 0
        }}>
          설정
        </h1>
      </div>

      {/* 사용자 정보 */}
      <div style={{
        padding: '24px',
        backgroundColor: 'white',
        marginBottom: '12px'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          marginBottom: '16px'
        }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            backgroundColor: '#FDB300',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px',
            fontWeight: 'bold',
            color: 'white'
          }}>
            {user?.name ? user.name.charAt(0) : '👤'}
          </div>
          <div>
            <div style={{
              fontSize: '18px',
              fontWeight: 'bold',
              marginBottom: '4px'
            }}>
              {user?.name || '게스트'}
            </div>
            {user?.email && (
              <div style={{
                fontSize: '14px',
                color: '#8B95A1'
              }}>
                {user.email}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 구독 정보 */}
      <div style={{
        padding: '24px',
        backgroundColor: 'white',
        marginBottom: '12px'
      }}>
        <h2 style={{
          fontSize: '16px',
          fontWeight: 'bold',
          marginBottom: '16px'
        }}>
          내 구독 게임
        </h2>

        {subsLoading ? (
          <div style={{ textAlign: 'center', padding: '20px', color: '#8B95A1' }}>
            로딩 중...
          </div>
        ) : subscriptions.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: '#8B95A1'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>📭</div>
            <div style={{ fontSize: '14px' }}>구독한 게임이 없습니다</div>
            <div style={{ fontSize: '12px', marginTop: '8px' }}>
              게임 목록에서 원하는 게임을 구독해보세요
            </div>
          </div>
        ) : (
          <div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '16px',
              marginBottom: '16px'
            }}>
              <div style={{
                textAlign: 'center',
                padding: '16px',
                backgroundColor: '#F8F9FA',
                borderRadius: '8px'
              }}>
                <div style={{
                  fontSize: '24px',
                  fontWeight: 'bold',
                  color: '#3182F6',
                  marginBottom: '4px'
                }}>
                  {new Set(subscriptions.map(s => s.gameId)).size}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#8B95A1'
                }}>
                  구독 게임
                </div>
              </div>
              <div style={{
                textAlign: 'center',
                padding: '16px',
                backgroundColor: '#F8F9FA',
                borderRadius: '8px'
              }}>
                <div style={{
                  fontSize: '24px',
                  fontWeight: 'bold',
                  color: '#FDB300',
                  marginBottom: '4px'
                }}>
                  {subscriptions.length}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#8B95A1'
                }}>
                  구독 소식
                </div>
              </div>
              <div style={{
                textAlign: 'center',
                padding: '16px',
                backgroundColor: '#F8F9FA',
                borderRadius: '8px'
              }}>
                <div style={{
                  fontSize: '24px',
                  fontWeight: 'bold',
                  color: '#6DD430',
                  marginBottom: '4px'
                }}>
                  {subscriptions.length * 5}+
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#8B95A1'
                }}>
                  받은 알림
                </div>
              </div>
            </div>

            {/* 구독 목록 */}
            <div style={{
              borderTop: '1px solid #E5E8EB',
              paddingTop: '16px'
            }}>
              {subscriptions.map((sub) => (
                <div
                  key={sub.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 0',
                    borderBottom: '1px solid #F1F3F5'
                  }}
                >
                  <div>
                    <div style={{
                      fontSize: '14px',
                      fontWeight: '600',
                      marginBottom: '4px'
                    }}>
                      {sub.gameName}
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#8B95A1'
                    }}>
                      {sub.category}
                    </div>
                  </div>
                  <button
                    onClick={async () => {
                      if (window.confirm('구독을 취소하시겠습니까?')) {
                        try {
                          await subscriptionAPI.unsubscribe(sub.id);
                          window.location.reload(); // 간단한 새로고침
                        } catch (err) {
                          alert('구독 취소에 실패했습니다.');
                        }
                      }
                    }}
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      color: '#E03E3E',
                      backgroundColor: 'white',
                      border: '1px solid #E03E3E',
                      borderRadius: '6px',
                      cursor: 'pointer'
                    }}
                  >
                    취소
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 구독권 현황 */}
      <div style={{
        padding: '24px',
        backgroundColor: 'white',
        marginBottom: '12px'
      }}>
        <h2 style={{
          fontSize: '16px',
          fontWeight: 'bold',
          marginBottom: '16px'
        }}>
          구독권 현황
        </h2>
        {premiumStatus ? (
          <div style={{
            padding: '16px',
            backgroundColor: premiumStatus.isPremium ? '#F0F9FF' : '#F8F9FA',
            borderRadius: '8px',
            border: premiumStatus.isPremium ? '1px solid #BFDBFE' : '1px solid #E5E8EB'
          }}>
            {premiumStatus.isPremium ? (
              <>
                <div style={{
                  fontSize: '14px',
                  fontWeight: 'bold',
                  color: '#1E40AF',
                  marginBottom: '8px'
                }}>
                  {premiumStatus.subscriptionType === 'free_ad' ? '📺 광고 구독권' : '🏪 프리미엄 구독권'}
                </div>
                <div style={{
                  fontSize: '13px',
                  color: '#4E5968',
                  marginBottom: '4px'
                }}>
                  만료일: {premiumStatus.expiresAt && new Date(premiumStatus.expiresAt).toLocaleDateString()}
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#8B95A1'
                }}>
                  {premiumStatus.subscriptionType === 'free_ad'
                    ? '게임 1개 구독 가능'
                    : '모든 게임 구독 가능'}
                </div>
              </>
            ) : (
              <>
                <div style={{
                  fontSize: '14px',
                  color: '#8B95A1',
                  marginBottom: '8px'
                }}>
                  구독권이 없습니다
                </div>
                <div style={{
                  fontSize: '12px',
                  color: '#8B95A1'
                }}>
                  홈 화면에서 광고를 보거나 프리미엄 구독권을 구매하세요
                </div>
              </>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#8B95A1' }}>
            로딩 중...
          </div>
        )}
      </div>

      {/* 앱 정보 */}
      <div style={{
        padding: '24px',
        backgroundColor: 'white',
        marginBottom: '12px'
      }}>
        <h2 style={{
          fontSize: '16px',
          fontWeight: 'bold',
          marginBottom: '16px'
        }}>
          앱 정보
        </h2>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '12px 0',
          borderBottom: '1px solid #F1F3F5'
        }}>
          <span style={{ fontSize: '14px', color: '#4E5968' }}>버전</span>
          <span style={{ fontSize: '14px', color: '#8B95A1' }}>1.0.0</span>
        </div>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '12px 0'
        }}>
          <span style={{ fontSize: '14px', color: '#4E5968' }}>문의</span>
          <span style={{ fontSize: '14px', color: '#8B95A1' }}>farmhoney1298@naver.com</span>
        </div>
      </div>

      {/* Game Honey API 테스트 */}
      <div style={{
        padding: '24px',
        backgroundColor: 'white',
        marginBottom: '12px'
      }}>
        <h2 style={{
          fontSize: '16px',
          fontWeight: 'bold',
          marginBottom: '16px'
        }}>
          🧪 Game Honey API
        </h2>
        <div style={{
          fontSize: '12px',
          color: '#8B95A1',
          marginBottom: '16px'
        }}>
          개발/디버깅용 테스트 도구
        </div>
        <button
          onClick={async () => {
            try {
              setSendingPush(true);
              const result = await testAPI.sendTestPush(
                '[테스트] Game Honey 푸시 알림',
                '푸시 알림 테스트가 성공적으로 발송되었습니다! 🎉'
              );

              if (result.success) {
                alert(`✅ ${result.message}\n\n토스 앱에서 알림을 확인하세요.`);
              } else {
                alert(`❌ 푸시 알림 발송 실패`);
              }
            } catch (error: any) {
              console.error('푸시 알림 테스트 오류:', error);
              if (error.response?.data?.error) {
                alert(`❌ ${error.response.data.error}`);
              } else {
                alert(`❌ 오류 발생\n\n${error.message || '알 수 없는 오류'}`);
              }
            } finally {
              setSendingPush(false);
            }
          }}
          disabled={sendingPush}
          style={{
            width: '100%',
            padding: '16px',
            fontSize: '14px',
            fontWeight: 'bold',
            color: 'white',
            backgroundColor: sendingPush ? '#B0B8C1' : '#3182F6',
            border: 'none',
            borderRadius: '12px',
            cursor: sendingPush ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            opacity: sendingPush ? 0.7 : 1
          }}
        >
          <span style={{ fontSize: '18px' }}>🔔</span>
          <span>{sendingPush ? '발송 중...' : '테스트 푸시 알림 보내기'}</span>
        </button>
        <div style={{
          marginTop: '12px',
          padding: '12px',
          backgroundColor: '#F8F9FA',
          borderRadius: '8px',
          fontSize: '11px',
          color: '#8B95A1',
          lineHeight: '1.5'
        }}>
          <strong>알림:</strong> 이 버튼을 누르면 현재 로그인한 계정으로 테스트 푸시 알림이 발송됩니다. 토스 앱의 알림센터에서 확인하세요.
        </div>
      </div>
    </div>
  );
}
