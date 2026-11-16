import { CircleAlert, LoaderCircle } from 'lucide-react';
import type { ReactNode } from 'react';

/** Estados de carga, permisos y error presentados dentro del propio workspace. */
export function WorkspaceMessage({
  kind,
  title,
  detail,
  children,
}: {
  kind: 'loading' | 'problem';
  title: string;
  detail?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className="frotis-v3-message"
      role={kind === 'loading' ? 'status' : 'alert'}
      aria-live={kind === 'loading' ? 'polite' : undefined}
    >
      {kind === 'loading'
        ? <LoaderCircle className="frotis-v3-message-icon frotis-v3-spin" aria-hidden="true" />
        : <CircleAlert className="frotis-v3-message-icon" aria-hidden="true" />}
      <h2>{title}</h2>
      {detail ? <p>{detail}</p> : null}
      {children ? <div className="frotis-v3-message-actions">{children}</div> : null}
    </div>
  );
}
