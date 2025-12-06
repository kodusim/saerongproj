import { Asset } from '@toss/tds-mobile';
import { colors } from '@toss/tds-colors';
import { Spacing } from './Spacing';

export default function Loading() {
  return (
    <div style={styles.container}>
      <div style={styles.content}>
        <h2 style={styles.title}>
          AI 사진관에서
          <br />
          프로필 사진을 만들고 있어요
        </h2>

        <Spacing size={12} />

        <p style={styles.subtitle}>잠시만 기다려주세요</p>

        <Spacing size={60} />

        <Asset.Lottie
          frameShape={{ width: 375 }}
          src="https://static.toss.im/lotties/loading/load-ripple.json"
          loop={true}
          speed={1}
          aria-hidden={true}
        />
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    padding: '20px',
    background: `linear-gradient(180deg, ${colors.blue50} 0%, ${colors.grey50} 100%)`,
  },
  content: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    maxWidth: '400px',
    width: '100%',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    color: colors.grey900,
    textAlign: 'center' as const,
    margin: 0,
    letterSpacing: '-0.4px',
  },
  subtitle: {
    fontSize: '15px',
    fontWeight: 400,
    color: colors.grey600,
    textAlign: 'center' as const,
    margin: 0,
    lineHeight: 1.5,
  },
};

