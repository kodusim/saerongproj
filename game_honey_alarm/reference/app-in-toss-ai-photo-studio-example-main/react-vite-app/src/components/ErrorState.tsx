import { Asset, Result } from '@toss/tds-mobile';

interface ErrorStateProps {
  title?: string;
  description?: string;
  detail?: string;
  onRetry: () => void;
}

export default function ErrorState({
  title = '오류가 발생했어요',
  description = '페이지를 불러올 수 없습니다\n다시 시도해주세요',
  detail,
  onRetry,
}: ErrorStateProps) {
  const descriptionDetail = detail ? detail : description;

  return (
    <div style={{ padding: '20px' }}>
      <Result
        figure={<Asset.Icon name="icn-info-line" frameShape={Asset.frameShape.CleanH24} />}
        title={title}
        description={descriptionDetail}
        button={<Result.Button onClick={onRetry}>재시도</Result.Button>}
      />
    </div>
  );
}

