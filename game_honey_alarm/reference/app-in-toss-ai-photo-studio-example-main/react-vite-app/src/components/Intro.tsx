import { useState } from 'react';
import { Spacing } from './Spacing';
import { Button, ListRow, Asset } from '@toss/tds-mobile';
import { colors } from '@toss/tds-colors';

interface IntroScreenProps {
  onAlbumSelect: () => void;
  onCameraOpen: () => void;
  error?: string;
}

export default function IntroScreen({ onAlbumSelect, onCameraOpen, error }: IntroScreenProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleCameraClick = () => {
    setIsOpen(false);
    onCameraOpen();
  };

  const handleAlbumClick = () => {
    setIsOpen(false);
    onAlbumSelect();
  };

  return (
    <div style={styles.container}>
      <Spacing size={40} />

      <div style={styles.heroSection}>
        <h1 style={styles.title}>
          일상 셀카 한장으로
          <br />
          전문 프로필 사진 완성
        </h1>

        <Spacing size={12} />

        <p style={styles.subtitle}>
          AI가 만드는 프로필 사진
        </p>
      </div>

      <Spacing size={48} />

      <div style={styles.stepContainer}>
        <h3 style={styles.sectionTitle}>
          이렇게 사용해요
        </h3>

        <div style={styles.stepList}>
          {[
            { number: '1', text: '얼굴 사진 한 장 준비', iconSrc: 'u1F4F8.png', desc: '갤러리나 카메라로' },
            { number: '2', text: '잠깐의 기다림', iconSrc: 'u23F3.png', desc: '광고 시청 후' },
            { number: '3', text: '프로필 사진 완성', iconSrc: 'u1F5BC.png', desc: 'AI가 만든 사진' }
          ].map((step) => (
            <div key={step.number} style={styles.stepCard}>
              <div style={styles.stepIconWrapper}>
                <Asset.Image
                  frameShape={Asset.frameShape.CleanW24}
                  backgroundColor="transparent"
                  src={`https://static.toss.im/2d-emojis/png/4x/${step.iconSrc}`}
                  aria-hidden={true}
                  style={{ aspectRatio: '1/1' }}
                />
              </div>
              <div style={styles.stepContent}>
                <p style={styles.stepText}>{step.text}</p>
                <p style={styles.stepDesc}>{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Spacing size={100} />

      {error && (
        <div style={styles.errorContainer}>
          <p style={styles.errorText}>{error}</p>
          <Spacing size={16} />
        </div>
      )}

      <div style={styles.buttonContainer}>
        <Button
          color="primary"
          variant="fill"
          size="large"
          display="block"
          onClick={() => setIsOpen(true)}
        >
          시작하기
        </Button>
      </div>

      {isOpen && (
        <>
          <div style={styles.overlay} onClick={() => setIsOpen(false)} />
          <div style={styles.modal}>
            <h3 style={styles.modalTitle}>사진 선택</h3>
            <Spacing size={20} />

            <div style={styles.listContainer}>
              <ListRow
                onClick={handleCameraClick}
                left={
                  <div style={styles.modalIconWrapper}>
                    <Asset.Image
                      frameShape={Asset.frameShape.CleanW24}
                      backgroundColor="transparent"
                      src="https://static.toss.im/2d-emojis/png/4x/u1F4F8.png"
                      aria-hidden={true}
                      style={{ aspectRatio: '1/1' }}
                    />
                  </div>
                }
                contents={
                  <div style={styles.listRowText}>사진 촬영</div>
                }
                withTouchEffect
              />
              <div style={styles.divider} />
              <ListRow
                onClick={handleAlbumClick}
                left={
                  <div style={styles.modalIconWrapper}>
                    <Asset.Image
                      frameShape={Asset.frameShape.CleanW24}
                      backgroundColor="transparent"
                      src="https://static.toss.im/2d-emojis/png/4x/u1F5BC.png"
                      aria-hidden={true}
                      style={{ aspectRatio: '1/1' }}
                    />
                  </div>
                }
                contents={
                  <div style={styles.listRowText}>앨범에서 선택</div>
                }
                withTouchEffect
              />
            </div>

            <Spacing size={20} />

            <Button
              color="dark"
              variant="weak"
              size="large"
              display="block"
              onClick={() => setIsOpen(false)}
            >
              취소
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    minHeight: '100vh',
    padding: '20px',
    background: `linear-gradient(180deg, ${colors.blue50} 0%, ${colors.grey50} 100%)`,
    paddingBottom: '120px',
  },
  heroSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    textAlign: 'center' as const,
  },
  transformContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  beforePhoto: {
    width: '80px',
    height: '80px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.grey100,
    borderRadius: '16px',
  },
  arrowContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrow: {
    fontSize: '32px',
    color: colors.blue500,
    fontWeight: 600,
  },
  afterPhoto: {
    width: '80px',
    height: '80px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.blue50,
    borderRadius: '16px',
    border: `1px solid ${colors.blue100}`,
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    color: colors.grey900,
    textAlign: 'center' as const,
    margin: 0,
    lineHeight: 1.4,
    letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: '16px',
    fontWeight: 400,
    color: colors.grey700,
    textAlign: 'center' as const,
    margin: 0,
    lineHeight: 1.5,
  },
  stepContainer: {
    width: '100%',
    maxWidth: '400px',
    padding: '0 4px',
  },
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 700,
    color: colors.grey900,
    margin: '0 0 20px 0',
    letterSpacing: '-0.3px',
  },
  stepList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  },
  stepCard: {
    display: 'flex',
    alignItems: 'center',
    padding: '20px',
    backgroundColor: colors.white,
    borderRadius: '16px',
    transition: 'transform 0.2s ease',
    border: `1px solid ${colors.grey100}`,
  },
  stepIconWrapper: {
    width: '48px',
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.blue50,
    borderRadius: '50%',
    marginRight: '16px',
    flexShrink: 0,
  },
  stepContent: {
    flex: 1,
  },
  stepText: {
    fontSize: '16px',
    fontWeight: 600,
    color: colors.grey900,
    margin: '0 0 4px 0',
    letterSpacing: '-0.2px',
  },
  stepDesc: {
    fontSize: '13px',
    fontWeight: 400,
    color: colors.grey600,
    margin: 0,
  },
  errorContainer: {
    width: '100%',
    maxWidth: '400px',
    padding: '12px 16px',
    backgroundColor: colors.red50,
    borderRadius: '12px',
  },
  errorText: {
    fontSize: '14px',
    fontWeight: 400,
    color: colors.red600,
    textAlign: 'center' as const,
    margin: 0,
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
  overlay: {
    position: 'fixed' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 1000,
  },
  modal: {
    position: 'fixed' as const,
    bottom: 0,
    left: '50%',
    transform: 'translateX(-50%)',
    width: '100%',
    maxWidth: '480px',
    backgroundColor: colors.white,
    borderTopLeftRadius: '24px',
    borderTopRightRadius: '24px',
    padding: '28px 20px',
    paddingBottom: 'max(32px, env(safe-area-inset-bottom))',
    zIndex: 1001,
    borderTop: `1px solid ${colors.grey100}`,
  },
  modalTitle: {
    fontSize: '20px',
    fontWeight: 700,
    color: colors.grey900,
    margin: 0,
    letterSpacing: '-0.4px',
    textAlign: 'center' as const,
  },
  listContainer: {
    borderRadius: '12px',
    overflow: 'hidden',
  },
  listRowText: {
    fontSize: '16px',
    fontWeight: 600,
    color: colors.grey900,
    letterSpacing: '-0.2px',
  },
  divider: {
    height: '1px',
    backgroundColor: colors.grey100,
    margin: '0 16px',
  },
  modalIconWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '24px',
    height: '24px',
  },
};

