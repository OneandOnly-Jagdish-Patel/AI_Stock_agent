interface Props {
  message: string;
}

export function StatusBanner({ message }: Props) {
  return (
    <div className="status-banner" role="status">
      {message}
    </div>
  );
}
