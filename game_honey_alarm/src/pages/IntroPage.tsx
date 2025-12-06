import { useNavigate } from 'react-router-dom';
import { Button } from '@toss/tds-mobile';
import { colors } from '@toss/tds-colors';
import { Spacing } from '../components/Spacing';

export default function IntroPage() {
  const navigate = useNavigate();

  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      minHeight: '100vh',
      padding: '20px',
      paddingBottom: '120px',
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '100%',
      padding: '16px 0',
    },
    logo: {
      width: '80px',
      height: '80px',
      backgroundColor: '#FFB800',
      borderRadius: '20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '40px',
      fontWeight: 700,
      color: colors.white,
    },
    title: {
      fontSize: '24px',
      fontWeight: 700,
      color: colors.grey900,
      textAlign: 'center' as const,
      lineHeight: 1.4,
    },
    hero: {
      textAlign: 'center' as const,
      padding: '60px 20px',
      backgroundColor: colors.grey50,
      borderRadius: '16px',
      width: '100%',
    },
    heroEmoji: {
      fontSize: '48px',
    },
    heroText: {
      marginTop: '12px',
      color: colors.grey700,
      fontSize: '14px',
    },
    guideTitle: {
      fontSize: '16px',
      fontWeight: 700,
      color: colors.grey900,
      marginBottom: '20px',
    },
    stepRow: {
      display: 'flex',
      gap: '12px',
      marginBottom: '16px',
    },
    stepNumber: {
      width: '28px',
      height: '28px',
      backgroundColor: '#FFB800',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: colors.white,
      fontWeight: 700,
      fontSize: '14px',
      flexShrink: 0,
    },
    stepText: {
      fontSize: '15px',
      fontWeight: 500,
      color: colors.grey900,
    },
    buttonContainer: {
      width: '100%',
      maxWidth: '400px',
      position: 'fixed' as const,
      bottom: '20px',
      left: '50%',
      transform: 'translateX(-50%)',
      padding: '0 20px',
    },
  };

  return (
    <div style={styles.container}>
      {/* 헤더 */}
      <header style={styles.header}>
        <h1 style={{ fontSize: '18px', fontWeight: 600, color: colors.grey900 }}>
          게임 하니
        </h1>
      </header>

      <Spacing size={40} />

      {/* 로고 */}
      <div style={styles.logo}>GH</div>

      <Spacing size={40} />

      {/* 타이틀 */}
      <h2 style={styles.title}>
        내가 원하는 게임의 소식을
        <br />
        알림으로
      </h2>

      <Spacing size={40} />

      {/* 히어로 */}
      <div style={styles.hero}>
        <div style={styles.heroEmoji}>🎮</div>
        <p style={styles.heroText}>게임 소식을 한눈에</p>
      </div>

      <Spacing size={40} />

      {/* 가이드 */}
      <div style={{ width: '100%' }}>
        <h3 style={styles.guideTitle}>게임 알림 받는법</h3>

        <div style={styles.stepRow}>
          <div style={styles.stepNumber}>1</div>
          <p style={styles.stepText}>원하는 게임 검색</p>
        </div>

        <div style={styles.stepRow}>
          <div style={styles.stepNumber}>2</div>
          <p style={styles.stepText}>원하는 소식 체크</p>
        </div>

        <div style={styles.stepRow}>
          <div style={styles.stepNumber}>3</div>
          <p style={styles.stepText}>알림 받기</p>
        </div>
      </div>

      {/* 하단 버튼 */}
      <div style={styles.buttonContainer}>
        <Button color="primary" variant="fill" size="large" display="block" onClick={() => navigate('/login')}>
          다음
        </Button>
      </div>
    </div>
  );
}
