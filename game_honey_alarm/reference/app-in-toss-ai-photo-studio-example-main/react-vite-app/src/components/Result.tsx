import { saveBase64Data } from '@apps-in-toss/web-framework';
import { colors } from '@toss/tds-colors';
import { BottomCTA, CTAButton } from '@toss/tds-mobile';
import { Spacing } from './Spacing';

interface ResultProps {
  imageUrl: string;
  onGoHome: () => void;
}

export default function Result({ imageUrl, onGoHome }: ResultProps) {
  const handleDownload = async () => {
    try {
      // imageUrl이 data URI인 경우 직접 사용
      if (imageUrl.startsWith('data:')) {
        const base64Data = imageUrl.split(',')[1];
        const mimeType = imageUrl.match(/data:([^;]+);/)?.[1] || 'image/png';

        await saveBase64Data({
          data: base64Data,
          fileName: `ai-profile-${Date.now()}.png`,
          mimeType,
        });
        return;
      }

      // URL인 경우 fetch로 가져오기
      const response = await fetch(imageUrl);
      const blob = await response.blob();

      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          if (typeof reader.result === 'string') {
            resolve(reader.result);
          } else {
            reject(new Error('이미지 데이터를 읽을 수 없습니다.'));
          }
        };
        reader.onerror = () => {
          reject(reader.error ?? new Error('이미지 데이터를 읽는 중 오류가 발생했습니다.'));
        };
        reader.readAsDataURL(blob);
      });

      const base64Data = dataUrl.split(',')[1];

      if (!base64Data) {
        throw new Error('잘못된 이미지 데이터입니다.');
      }

      await saveBase64Data({
        data: base64Data,
        fileName: `ai-profile-${Date.now()}.png`,
        mimeType: blob.type || 'image/png',
      });
    } catch (error) {
      console.error('다운로드 실패:', error);
      alert('다운로드에 실패했습니다.');
    }
  };

  return (
    <div style={styles.container}>
      <Spacing size={24} />

      <h2 style={styles.title}>
        AI 사진관에서 만든
        <br />
        프로필 사진이에요
      </h2>

      <Spacing size={8} />

      <p style={styles.subtitle}>저장하고 친구들에게 공유해보세요</p>

      <Spacing size={24} />

      {imageUrl && (
        <div style={styles.galleryFrame}>
          <div style={styles.imageWrapper}>
            <img src={imageUrl} alt="AI 사진관 작품" style={styles.resultImage} />
          </div>
        </div>
      )}

      <BottomCTA.Double
        leftButton={
          <CTAButton display="block" color="dark" variant="fill" onClick={onGoHome}>
            처음으로
          </CTAButton>
        }
        rightButton={
          <CTAButton display="block" color="primary" variant="fill" onClick={handleDownload}>
            저장하기
          </CTAButton>
        }
      />
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
    paddingBottom: '180px',
  },
  title: {
    fontSize: '24px',
    fontWeight: 700,
    color: colors.grey900,
    textAlign: 'center' as const,
    margin: 0,
    letterSpacing: '-0.4px',
    lineHeight: 1.4,
  },
  subtitle: {
    fontSize: '15px',
    fontWeight: 400,
    color: colors.grey600,
    textAlign: 'center' as const,
    margin: 0,
    lineHeight: 1.5,
  },
  galleryFrame: {
    width: '100%',
    maxWidth: '360px',
  },
  imageWrapper: {
    position: 'relative' as const,
    width: '100%',
    padding: '20px',
    backgroundColor: colors.white,
    borderRadius: '16px',
    border: `1px solid ${colors.grey100}`,
  },
  resultImage: {
    width: '100%',
    height: 'auto',
    borderRadius: '8px',
    display: 'block',
  },
};

