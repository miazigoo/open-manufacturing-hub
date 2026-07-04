import { CopyButton } from './CopyButton';

interface EndpointUrlBoxProps {
  url: string;
  label?: string;
}

export function EndpointUrlBox({ url, label = 'Endpoint URL' }: EndpointUrlBoxProps) {
  return (
    <div className="endpoint-url-box">
      <span>{label}</span>
      <code>{url}</code>
      <CopyButton value={url} label="Copy URL" />
    </div>
  );
}
