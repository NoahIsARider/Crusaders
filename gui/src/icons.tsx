import type { JSX } from "react";

const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function IconShield(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <path
        {...stroke}
        d="M12 3l7 3v5c0 4.6-3 8.2-7 10-4-1.8-7-5.4-7-10V6l7-3z"
      />
      <path {...stroke} d="M9.5 12l1.8 1.8L14.8 9.6" />
    </svg>
  );
}

export function IconGauge(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <path {...stroke} d="M5 19a9 9 0 1114 0" />
      <path {...stroke} d="M12 13l4-5" />
      <circle cx="12" cy="14" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconPulse(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <path {...stroke} d="M3 12h4l2.5-6 4 12 2.5-6h5" />
    </svg>
  );
}

export function IconBot(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <rect x="4" y="8" width="16" height="11" rx="3" {...stroke} />
      <path {...stroke} d="M12 8V5m0 0l-2.5-2M12 5l2.5-2" />
      <circle cx="9.2" cy="13.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="14.8" cy="13.5" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconUser(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <circle cx="12" cy="8" r="4" {...stroke} />
      <path {...stroke} d="M4.5 20a7.5 7.5 0 0115 0" />
    </svg>
  );
}

export function IconLayers(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <path {...stroke} d="M12 3l9 5-9 5-9-5 9-5z" />
      <path {...stroke} d="M3 13l9 5 9-5" />
    </svg>
  );
}

export function IconTask(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <path {...stroke} d="M9 4h11v4H9zM4 4h3v4H4zM9 10h11v4H9zM4 10h3v4H4zM9 16h11v4H9zM4 16h3v4H4z" />
    </svg>
  );
}

export function IconStep(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none" />
      <path {...stroke} d="M12 2v4.4M12 17.6V22M2 12h4.4M17.6 12H22" />
      <circle cx="12" cy="12" r="7.5" {...stroke} />
    </svg>
  );
}

export function IconGrip(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" {...props}>
      <circle cx="9" cy="6" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="15" cy="6" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="9" cy="12" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="15" cy="12" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="9" cy="18" r="1.3" fill="currentColor" stroke="none" />
      <circle cx="15" cy="18" r="1.3" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconPlus(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" {...props}>
      <path {...stroke} d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function IconTrash(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" {...props}>
      <path {...stroke} d="M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13" />
    </svg>
  );
}

export function IconClose(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" {...props}>
      <path {...stroke} d="M5 5l14 14M19 5L5 19" />
    </svg>
  );
}

export function IconPlay(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" {...props}>
      <path d="M7 4.5v15l13-7.5-13-7.5z" fill="currentColor" />
    </svg>
  );
}

export function IconSpark(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" {...props}>
      <path
        d="M12 3l2 5.5L19.5 10 14 12.5 12 18l-2-5.5L4.5 10 10 8.5 12 3z"
        fill="currentColor"
      />
    </svg>
  );
}

export function IconBolt(props: JSX.IntrinsicElements["svg"]) {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" {...props}>
      <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" fill="currentColor" />
    </svg>
  );
}

const iconMap: Record<string, (p: JSX.IntrinsicElements["svg"]) => JSX.Element> = {
  shield: IconShield,
  gauge: IconGauge,
  pulse: IconPulse,
  bot: IconBot,
  user: IconUser,
  layers: IconLayers,
};

export function PolicyIcon({ name, size = 16 }: { name: string; size?: number }) {
  const Cmp = iconMap[name] ?? IconShield;
  return <Cmp width={size} height={size} />;
}
