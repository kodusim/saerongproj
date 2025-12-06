import { useState, useRef, useEffect, ChangeEvent } from 'react';
import imageCompression from 'browser-image-compression';
import {
  GoogleAdMob,
  fetchAlbumPhotos,
  openCamera,
  FetchAlbumPhotosPermissionError,
  OpenCameraPermissionError,
} from '@apps-in-toss/web-framework';
import ErrorState from '../components/ErrorState';
import IntroScreen from '../components/Intro';
import Loading from '../components/Loading';
import Result from '../components/Result';

// ============================================
// 타입 정의
// ============================================

/** 애플리케이션의 현재 화면 상태 */
type Step = 'intro' | 'loading' | 'result' | 'error';

/** 광고 타입: 보상형 또는 전면형 */
type AdType = 'rewarded' | 'interstitial';

/** 사용자가 선택한 이미지 데이터 (파일 또는 Data URI) */
interface SelectedImage {
  file?: File;
  dataUri?: string;
}

// ============================================
// 상수 정의
// ============================================

/** 광고 그룹 ID */
const AD_GROUP_IDS = {
  REWARDED: 'ait-ad-test-rewarded-id',      // 보상형 광고
  INTERSTITIAL: 'ait-ad-test-interstitial-id',  // 전면형 광고
} as const;

/** 광고 재시도 설정 */
const AD_RETRY_CONFIG = {
  MAX_ATTEMPTS: 3,                     // 최대 재시도 횟수
  DELAYS_MS: [1000, 3000, 5000],      // 각 재시도 간 대기 시간 (ms)
  WAIT_TIMEOUT_MS: 10000,             // 광고 로드 최대 대기 시간 (10초)
} as const;

/** 이미지 압축 옵션 */
const IMAGE_COMPRESSION_OPTIONS = {
  maxSizeMB: 1,                       // 최대 파일 크기 (MB)
  maxWidthOrHeight: 512,              // 최대 가로/세로 크기 (px)
  useWebWorker: true,                 // Web Worker 사용 여부
} as const;

/** API 요청 기본 설정 */
const DEFAULT_API_URL = 'https://yourgooglecloud-xxxx.us-central1.run.app';
const DEFAULT_REQUEST_TIMEOUT_MS = 90000;   // 90초
const DEFAULT_RETRY_LIMIT = 3;              // 최대 재시도 횟수
const DEFAULT_RETRY_DELAY_MS = 3000;        // 재시도 간 대기 시간 (3초)

// ============================================
// 유틸리티 함수
// ============================================

/**
 * 지정된 시간(밀리초)만큼 대기하는 Promise를 반환합니다.
 * @param ms 대기 시간 (밀리초)
 */
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * 이미지 파일을 압축합니다.
 * @param file 압축할 이미지 파일
 * @returns 압축된 이미지 파일
 */
const compressImage = async (file: File): Promise<File> => {
  const compressed = await imageCompression(file, IMAGE_COMPRESSION_OPTIONS);

  // 이미 File 객체인 경우 그대로 반환
  if (compressed instanceof File) {
    return compressed;
  }

  // Blob인 경우 File 객체로 변환
  const fileName = file.name || 'photo.jpg';
  const mimeType = (compressed as Blob).type || file.type || 'image/jpeg';

  return new File([compressed], fileName, { type: mimeType });
};

/**
 * 환경 변수 값을 숫자로 파싱합니다.
 * 유효하지 않은 값이면 fallback을 반환합니다.
 * @param value 환경 변수 값
 * @param fallback 기본값
 * @returns 파싱된 숫자 또는 기본값
 */
const parseNumberEnv = (value: string | number | undefined, fallback: number): number => {
  if (value === undefined) {
    return fallback;
  }

  const parsed = typeof value === 'number' ? value : Number(value);

  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
};

// ============================================
// 메인 컴포넌트
// ============================================

export default function ProfilePage() {
  // ============================================
  // 상태 관리
  // ============================================

  /** 현재 화면 상태 */
  const [step, setStep] = useState<Step>('intro');

  /** 생성된 프로필 이미지 URL */
  const [imageUrl, setImageUrl] = useState('');

  /** 에러 메시지 */
  const [error, setError] = useState('');

  /** 광고 로드 완료 여부 */
  const [adLoaded, setAdLoaded] = useState(false);

  /** 광고 표시 중 여부 */
  const [adShowing, setAdShowing] = useState(false);

  /** 현재 광고 타입 (보상형 또는 전면형) */
  const [adType, setAdType] = useState<AdType>('rewarded');

  /** 광고 로드 대기 중 여부 */
  const [waitingForAd, setWaitingForAd] = useState(false);

  // ============================================
  // Refs
  // ============================================

  /** 파일 입력 요소에 대한 참조 */
  const fileInputRef = useRef<HTMLInputElement>(null);

  /** 사용자가 선택한 이미지 데이터 */
  const imageRef = useRef<SelectedImage | null>(null);

  /** 광고 cleanup 함수 */
  const cleanupRef = useRef<(() => void) | undefined>();

  /** 보상형 광고 보상 획득 여부 */
  const rewardEarnedRef = useRef(false);

  /** 광고 로드 재시도 횟수 */
  const retryCountRef = useRef(0);

  /** 광고 로드 재시도 타이머 */
  const retryTimeoutRef = useRef<NodeJS.Timeout | undefined>();

  /** 광고 로드 대기 타이머 */
  const adWaitTimeoutRef = useRef<NodeJS.Timeout | undefined>();

  /** 현재 step의 최신 값을 유지 (이벤트 핸들러에서 사용) */
  const stepRef = useRef<Step>(step);

  // ============================================
  // Effect Hooks
  // ============================================

  /**
   * step이 변경될 때마다 ref 업데이트
   * - stepRef는 이벤트 핸들러에서 최신 step 값을 참조하기 위해 사용
   */
  useEffect(() => {
    stepRef.current = step;
  }, [step]);

  /**
   * 뒤로가기 이벤트 핸들러 (네비게이션 바 백버튼 제어)
   * - intro 화면에서는 앱 종료 허용
   * - 다른 화면에서는 intro로 이동
   */
  useEffect(() => {
    // 초기 history state 추가
    window.history.pushState({ page: 'app' }, '', '');

    const handlePopState = () => {
      const currentStep = stepRef.current;

      if (currentStep === 'intro') {
        // 인트로 화면에서는 앱 종료 허용
        return;
      }

      // 다른 화면에서는 history 다시 추가하고 인트로로 이동
      window.history.pushState({ page: 'app' }, '', '');
      handleGoHome();
    };

    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, []); // 한 번만 등록

  // ============================================
  // 광고 관련 함수
  // ============================================

  /**
   * 타임아웃 및 cleanup 정리 유틸리티
   */
  const clearAllTimers = () => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = undefined;
    }
    if (adWaitTimeoutRef.current) {
      clearTimeout(adWaitTimeoutRef.current);
      adWaitTimeoutRef.current = undefined;
    }
  };

  /**
   * 광고를 로드합니다.
   * @param type 로드할 광고 타입 ('rewarded' 또는 'interstitial')
   *
   * 동작 방식:
   * 1. 광고 지원 여부 확인
   * 2. 광고 로드 시도
   * 3. 실패 시 재시도 (최대 3회)
   * 4. 보상형 실패 시 전면형으로 전환
   */
  const loadAd = (type: AdType) => {
    try {
      const currentRetry = retryCountRef.current;
      const adGroupId = type === 'rewarded' ? AD_GROUP_IDS.REWARDED : AD_GROUP_IDS.INTERSTITIAL;
      const adTypeName = type === 'rewarded' ? '보상형' : '전면형';

      console.log(`\n📥 [${adTypeName}] 광고 로드 시도 ${currentRetry + 1}회`);

      // 광고 기능 지원 여부 확인
      const isSupported = GoogleAdMob.loadAppsInTossAdMob.isSupported?.();
      console.log('🔍 loadAppsInTossAdMob.isSupported():', isSupported);

      if (isSupported !== true) {
        console.warn(`❌ ${adTypeName} 광고 기능 미지원. isSupported:`, isSupported);

        // 보상형이 미지원이면 전면형으로 전환
        if (type === 'rewarded') {
          console.log('🔄 전면형 광고로 전환');
          setAdType('interstitial');
          retryCountRef.current = 0;
          loadAd('interstitial');
        } else {
          console.warn('   광고 없이 진행');
        }
        return;
      }

      // 기존 cleanup 함수 실행
      cleanupRef.current?.();
      cleanupRef.current = undefined;

      setAdLoaded(false);
      console.log(`🔄 ${adTypeName} 광고 로드 시작...`);

      // 광고 로드
      const cleanup = GoogleAdMob.loadAppsInTossAdMob({
        options: { adGroupId },
        onEvent: (event) => {
          if (event.type === 'loaded') {
            console.log(`✅ ${adTypeName} 광고 로드 완료:`, event.data);
            setAdLoaded(true);
            setAdType(type);
            retryCountRef.current = 0;
          }
        },
        onError: (loadError) => {
          console.error(`❌ ${adTypeName} 광고 로드 실패:`, loadError);
          setAdLoaded(false);

          const errorMessage = loadError?.message || JSON.stringify(loadError) || '';

          // "No ad to show" 에러인 경우 재시도
          if (errorMessage.includes('No ad to show')) {
            if (retryCountRef.current < AD_RETRY_CONFIG.MAX_ATTEMPTS) {
              const delay = AD_RETRY_CONFIG.DELAYS_MS[retryCountRef.current] || 5000;
              console.log(`⏱️ ${delay / 1000}초 후 ${adTypeName} 광고 재시도 (${retryCountRef.current + 1}/${AD_RETRY_CONFIG.MAX_ATTEMPTS})`);

              retryTimeoutRef.current = setTimeout(() => {
                retryCountRef.current += 1;
                loadAd(type);
              }, delay) as unknown as NodeJS.Timeout;
            } else {
              console.warn(`⚠️ ${adTypeName} 광고 ${AD_RETRY_CONFIG.MAX_ATTEMPTS}회 실패`);

              // 보상형 실패 시 전면형으로 전환
              if (type === 'rewarded') {
                console.log('🔄 전면형 광고로 전환');
                setAdType('interstitial');
                retryCountRef.current = 0;
                loadAd('interstitial');
              } else {
                console.warn('   광고 없이 진행');
                retryCountRef.current = 0;
              }
            }
          } else {
            // 기타 에러 발생 시
            console.error(`광고 로드 실패: ${errorMessage}`);

            if (type === 'rewarded') {
              console.warn('⚠️ 전면형 광고로 전환');
              setAdType('interstitial');
              retryCountRef.current = 0;
              loadAd('interstitial');
            } else {
              console.warn('⚠️ 광고 없이 진행');
            }
          }
        },
      });

      cleanupRef.current = cleanup;
    } catch (loadError) {
      console.error(`⚠️ ${type === 'rewarded' ? '보상형' : '전면형'} 광고 로드 예외:`, loadError);
      setAdLoaded(false);

      // 보상형 실패 시 전면형으로 전환
      if (type === 'rewarded') {
        console.warn('⚠️ 전면형 광고로 전환');
        setAdType('interstitial');
        retryCountRef.current = 0;
        loadAd('interstitial');
      } else {
        console.warn('⚠️ 광고 없이 진행');
      }
    }
  };

  /**
   * 컴포넌트 마운트 시 광고 로드 및 언마운트 시 정리
   */
  useEffect(() => {
    loadAd('rewarded');

    return () => {
      // cleanup 함수 호출
      cleanupRef.current?.();
      cleanupRef.current = undefined;

      // 타이머 정리
      clearAllTimers();
    };
  }, []);


  /**
   * 광고 로드 완료 시 대기 중이었다면 광고 표시
   */
  useEffect(() => {
    if (waitingForAd && adLoaded) {
      console.log('✅ 광고 로드 완료 - 광고 표시');
      setWaitingForAd(false);

      // 타이머 정리
      if (adWaitTimeoutRef.current) {
        clearTimeout(adWaitTimeoutRef.current);
        adWaitTimeoutRef.current = undefined;
      }

      showAd();
    }
  }, [adLoaded, waitingForAd]);

  // ============================================
  // 이미지 선택 관련 함수
  // ============================================

  /**
   * 파일을 처리하고 프로필 생성을 요청합니다.
   * @param file 사용자가 선택한 이미지 파일
   */
  const handleFile = async (file: File) => {
    setError('');

    try {
      const compressedFile = await compressImage(file);
      imageRef.current = { file: compressedFile };
      requestGeneration();
    } catch (err) {
      console.error('이미지 처리 실패', err);
      setError('이미지를 처리할 수 없어요. 다른 사진을 선택해주세요');
      setStep('error');
    }
  };

  /**
   * 파일 input 변경 이벤트 핸들러
   */
  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ''; // 같은 파일 재선택을 위해 초기화

    if (!file) {
      setError('사진을 선택해주세요');
      setStep('error');
      return;
    }

    await handleFile(file);
  };

  /**
   * 앨범에서 사진을 선택합니다.
   * - 앨범 권한 확인 및 요청
   * - 사진 선택 후 프로필 생성 요청
   */
  const pickFromAlbum = async () => {
    setError('');

    const supportsAlbum = typeof fetchAlbumPhotos === 'function';

    if (!supportsAlbum) {
      // 앨범 미지원 시 파일 선택기 사용 (fallback)
      fileInputRef.current?.click();
      return;
    }

    try {
      const currentPermission = await fetchAlbumPhotos.getPermission?.();

      if (currentPermission === 'denied') {
        const dialogResult = await fetchAlbumPhotos.openPermissionDialog?.();

        if (dialogResult !== 'allowed') {
          setError('앨범 권한이 필요해요');
          setStep('error');
          return;
        }
      }

      const photos = await fetchAlbumPhotos({
        maxCount: 1,
        maxWidth: 128,
        base64: true,
      });

      if (photos.length === 0) {
        setError('사진을 선택해주세요');
        setStep('error');
        return;
      }

      const normalizedDataUri = photos[0].dataUri.startsWith('data:')
        ? photos[0].dataUri
        : `data:image/jpeg;base64,${photos[0].dataUri}`;

      imageRef.current = { dataUri: normalizedDataUri };
      requestGeneration();
    } catch (error) {
      if (error instanceof FetchAlbumPhotosPermissionError) {
        setError('앨범 권한이 필요해요');
        setStep('error');
      } else {
        setError('사진을 불러올 수 없어요. 파일을 직접 선택해주세요');
        setStep('error');
      }
    }
  };

  /**
   * 카메라로 사진을 촬영합니다.
   * - 카메라 권한 확인 및 요청
   * - 촬영 후 프로필 생성 요청
   */
  const takePhoto = async () => {
    setError('');

    const supportsCamera = typeof openCamera === 'function';

    if (!supportsCamera) {
      // 카메라 미지원 시 파일 선택기 사용 (fallback)
      fileInputRef.current?.click();
      return;
    }

    try {
      const currentPermission = await openCamera.getPermission?.();

      if (currentPermission === 'denied') {
        const dialogResult = await openCamera.openPermissionDialog?.();

        if (dialogResult !== 'allowed') {
          setError('카메라 권한이 필요해요');
          setStep('error');
          return;
        }
      }

      const photo = await openCamera({
        maxWidth: 512,
        base64: true,
      });

      const normalizedDataUri = photo.dataUri.startsWith('data:')
        ? photo.dataUri
        : `data:image/jpeg;base64,${photo.dataUri}`;

      imageRef.current = { dataUri: normalizedDataUri };
      requestGeneration();
    } catch (error) {
      if (error instanceof OpenCameraPermissionError) {
        setError('카메라 권한이 필요해요');
        setStep('error');
      } else {
        setError('카메라를 열 수 없어요. 파일을 직접 선택해주세요');
        setStep('error');
      }
    }
  };

  // ============================================
  // 프로필 생성 관련 함수
  // ============================================

  /**
   * 프로필 생성을 요청합니다.
   * - 광고 표시 지원 여부 확인
   * - 광고 로드 대기 또는 즉시 표시
   * - 광고 미지원 시 바로 프로필 생성
   */
  const requestGeneration = () => {
    try {
      const isSupported = GoogleAdMob.showAppsInTossAdMob.isSupported?.();
      console.log('🔍 showAppsInTossAdMob.isSupported():', isSupported);
      console.log('📊 adLoaded 상태:', adLoaded);
      console.log('📊 광고 타입:', adType);

      if (isSupported !== true) {
        console.warn('광고 표시 기능 미지원. isSupported:', isSupported);
        setStep('loading');
        generateProfile();
        return;
      }

      // 광고 로드 중이라면 로딩 화면 표시하고 대기
      if (adLoaded === false) {
        console.log('⏳ 광고 로드 대기 중 - 로딩 화면 표시');
        setStep('loading');
        setWaitingForAd(true);

        // 최대 대기 시간 후 광고 없이 진행
        adWaitTimeoutRef.current = setTimeout(() => {
          console.warn(`⚠️ 광고 로드 타임아웃 (${AD_RETRY_CONFIG.WAIT_TIMEOUT_MS / 1000}초) - 광고 없이 진행`);
          setWaitingForAd(false);
          generateProfile();
        }, AD_RETRY_CONFIG.WAIT_TIMEOUT_MS) as unknown as NodeJS.Timeout;

        return;
      }

      // 광고가 이미 로드된 경우 바로 표시
      showAd();
    } catch (error) {
      console.error('❌ 광고 표시 중 예외 발생:', error);
      setStep('loading');
      generateProfile();
    }
  };

  /**
   * 광고를 표시합니다.
   * - 보상형: 보상 획득 여부에 따라 프로필 생성 진행
   * - 전면형: 광고 닫힘 시 바로 프로필 생성 진행
   */
  const showAd = () => {
    try {
      // 광고 타입에 따라 다른 ID 사용
      const adGroupId = adType === 'rewarded' ? AD_GROUP_IDS.REWARDED : AD_GROUP_IDS.INTERSTITIAL;
      const adTypeName = adType === 'rewarded' ? '보상형' : '전면형';

      console.log(`✅ [${adTypeName}] 광고 표시 시작`);
      setAdShowing(true);
      rewardEarnedRef.current = false;

      GoogleAdMob.showAppsInTossAdMob({
        options: { adGroupId },
        onEvent: (event) => {
          switch (event.type) {
            case 'requested':
              console.log(`✅ [${adTypeName}] 광고 표시 요청 완료`);
              break;

            case 'show':
              console.log(`✅ [${adTypeName}] 광고 컨텐츠 표시 시작`);
              break;

            case 'impression':
              console.log(`✅ [${adTypeName}] 광고 노출 완료`);
              break;

            case 'clicked':
              console.log(`✅ [${adTypeName}] 광고 클릭됨`);
              break;

            case 'userEarnedReward':
              // 보상형 광고만 해당
              console.log('🎁 보상 획득!', event.data);
              rewardEarnedRef.current = true;
              break;

            case 'dismissed':
              console.log(`[${adTypeName}] 광고 닫힘`);

              if (adType === 'rewarded') {
                // 보상형: 보상 획득 여부 확인
                if (rewardEarnedRef.current) {
                  console.log('✅ 보상형 광고 완료 - 프로필 생성 진행');
                  setStep('loading');
                  generateProfile();
                } else {
                  console.warn('⚠️ 보상형 광고 중도 종료 - 프로필 생성하지 않음');
                  setStep('intro');
                  setError('광고를 끝까지 시청해주세요');
                }
              } else {
                // 전면형: dismissed 이벤트에서 바로 프로필 생성
                console.log('✅ 전면형 광고 닫힘 - 프로필 생성 진행');
                setStep('loading');
                generateProfile();
              }

              // 상태 정리 및 다음 광고 로드
              setAdShowing(false);
              loadAd('rewarded'); // 다음엔 보상형부터 다시 시도
              break;

            case 'failedToShow':
              console.warn(`⚠️ [${adTypeName}] 광고 표시 실패 - 광고 없이 진행:`, event.data);
              setAdShowing(false);
              setStep('loading');
              generateProfile();
              loadAd('rewarded');
              break;
          }
        },
        onError: (showError) => {
          console.error(`❌ [${adTypeName}] 광고 표시 에러:`, showError);
          setAdShowing(false);
          console.warn('⚠️ 광고 표시 에러 발생 - 광고 없이 진행');
          setStep('loading');
          generateProfile();
          loadAd('rewarded');
        }
      });
    } catch (error) {
      console.error('❌ 광고 표시 중 예외 발생:', error);
      setAdShowing(false);
      setStep('loading');
      generateProfile();
      loadAd('rewarded');
    }
  };

  /**
   * 프로필 이미지를 생성합니다.
   * - API 호출하여 AI 프로필 생성
   * - 재시도 로직 포함 (타임아웃 발생 시)
   */
  const generateProfile = async () => {
    if (!imageRef.current) {
      setError('사진을 다시 선택해주세요');
      setStep('error');
      return;
    }

    // 환경 변수에서 설정 읽기
    const metaEnv = (import.meta as { env?: Record<string, string> }).env ?? {};
    const apiUrl = metaEnv.VITE_API_URL || DEFAULT_API_URL;
    const timeoutMs = parseNumberEnv(metaEnv.VITE_REQUEST_TIMEOUT_MS, DEFAULT_REQUEST_TIMEOUT_MS);
    const retryLimit = parseNumberEnv(metaEnv.VITE_REQUEST_RETRY_LIMIT, DEFAULT_RETRY_LIMIT);
    const retryDelay = parseNumberEnv(metaEnv.VITE_REQUEST_RETRY_DELAY_MS, DEFAULT_RETRY_DELAY_MS);

    try {
      // 이미지 데이터 준비 (Blob 또는 File 형태로 변환)
      let imageData: File | Blob;
      let fileName: string;

      if (imageRef.current.file) {
        // File은 이미 압축되어 있음 (handleFile에서 압축함)
        imageData = imageRef.current.file;
        fileName = imageRef.current.file.name || 'photo.jpg';
      } else if (imageRef.current.dataUri) {
        // DataURI를 Blob으로 변환
        const response = await fetch(imageRef.current.dataUri);
        imageData = await response.blob();
        fileName = 'photo.jpg';
      } else {
        throw new Error('이미지 데이터를 찾을 수 없습니다.');
      }

      /**
       * 타임아웃을 포함한 fetch 요청
       */
      const fetchWithTimeout = (url: string, options: RequestInit, timeout: number): Promise<Response> => {
        return Promise.race([
          fetch(url, options),
          new Promise<Response>((_, reject) =>
            setTimeout(() => reject(new Error('REQUEST_TIMEOUT')), timeout)
          )
        ]);
      };

      /**
       * API 요청 (재시도 로직 포함)
       * @param attempt 현재 시도 횟수
       */
      const request = async (attempt: number): Promise<Response> => {
        // 매 시도마다 FormData를 새로 생성
        const formData = new FormData();
        formData.append('image', imageData, fileName);

        try {
          const response = await fetchWithTimeout(
            `${apiUrl}/api/generate`,
            {
              method: 'POST',
              body: formData,
            },
            timeoutMs
          );

          return response;
        } catch (requestError) {
          // 타임아웃 발생 시 재시도
          if (
            attempt < retryLimit &&
            requestError instanceof Error &&
            requestError.message === 'REQUEST_TIMEOUT'
          ) {
            console.warn(`⏱️ 요청 타임아웃 - 재시도 ${attempt + 1}/${retryLimit}`);
            await sleep(retryDelay);
            return request(attempt + 1);
          }

          throw requestError;
        }
      };

      const res = await request(0);

      // HTTP 응답 확인
      if (!res.ok) {
        // 에러 응답 처리
        try {
          const errorData = await res.json();
          throw new Error(errorData.error || '프로필을 만들 수 없어요. 다시 시도해주세요');
        } catch (parseError) {
          // JSON 파싱 실패 시 기본 에러 메시지
          if (parseError instanceof Error && parseError.message) {
            throw parseError;
          }
          throw new Error('프로필을 만들 수 없어요. 다시 시도해주세요');
        }
      }

      // Content-Type 확인하여 응답 형식 판단
      const contentType = res.headers.get('content-type');

      if (contentType?.includes('application/json')) {
        // JSON 응답 (이미지 URL 반환)
        const data = await res.json();
        if (!data.success || !data.imageUrl) {
          throw new Error(data.error || '프로필을 만들 수 없어요. 다시 시도해주세요');
        }
        setImageUrl(data.imageUrl);
      } else {
        // 이미지 바이너리 직접 반환
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        setImageUrl(objectUrl);
      }

      setStep('result');
    } catch (err) {
      console.error('프로필 생성 실패', err);

      // 에러 타입에 따른 메시지 설정
      if (err instanceof Error && err.message === 'REQUEST_TIMEOUT') {
        setError('요청 시간이 너무 오래 걸려 중단되었어요. 잠시 후 다시 시도해주세요.');
      } else {
        setError(err instanceof Error ? err.message : '프로필을 만들 수 없어요. 다시 시도해주세요');
      }
      setStep('error');
    }
  };

  /**
   * 홈(인트로) 화면으로 이동합니다.
   * - 모든 상태를 초기화
   * - 새로운 광고 로드
   */
  const handleGoHome = () => {
    setStep('intro');
    setImageUrl('');
    setError('');
    imageRef.current = null;

    // 다음 생성을 위해 광고 로드
    loadAd('rewarded');
  };

  // ============================================
  // 렌더링
  // ============================================

  if (step === 'intro') {
    return (
      <>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <IntroScreen
          error={error}
          onAlbumSelect={pickFromAlbum}
          onCameraOpen={takePhoto}
        />
      </>
    );
  }

  if (step === 'loading') {
    return <Loading />;
  }

  if (step === 'result') {
    return (
      <Result
        imageUrl={imageUrl}
        onGoHome={handleGoHome}
      />
    );
  }

  return (
    <ErrorState
      description="예상치 못한 오류가 발생했어요."
      detail={error}
      onRetry={() => {
        setError('');
        setStep('intro');
      }}
    />
  );
}

