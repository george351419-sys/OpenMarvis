interface HorseLogoProps {
  size?: number;
  className?: string;
}

export function HorseLogo({ size = 72, className = "" }: HorseLogoProps) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 100 100"
      fill="none" xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* App icon background */}
      <rect width="100" height="100" rx="22" fill="#111111" />

      {/* ── Horse head silhouette (profile, facing left) ── */}
      {/* Main head + neck mass */}
      <path
        d="
          M62,16
          C65,10 70,9 72,14
          C70,18 66,20 63,22
          C67,26 70,32 70,40
          C70,50 64,58 56,62
          C52,64 48,66 46,70
          C44,74 44,80 48,82
          C52,84 56,82 58,78
          C60,74 60,68 62,64
          C68,60 74,52 74,42
          C74,32 70,24 64,18
          Z
        "
        fill="white"
      />
      {/* Head oval */}
      <path
        d="
          M36,30
          C34,24 36,16 42,14
          C48,12 56,14 60,20
          C64,26 63,36 58,42
          C54,46 48,48 42,46
          C36,44 32,38 36,30
          Z
        "
        fill="white"
      />
      {/* Muzzle / lower jaw */}
      <path
        d="
          M36,42
          C32,44 26,46 24,52
          C22,58 26,64 32,64
          C36,64 40,62 42,58
          C44,54 42,48 38,44
          Z
        "
        fill="white"
      />
      {/* Ear */}
      <path
        d="M58,14 L62,6 L68,12 L64,16 Z"
        fill="white"
      />
      {/* Mane strand 1 */}
      <path
        d="M65,20 C70,12 76,14 76,22 C72,22 68,22 65,20Z"
        fill="white"
      />
      {/* Mane strand 2 */}
      <path
        d="M66,28 C72,22 78,26 76,34 C72,32 68,30 66,28Z"
        fill="white"
      />
      {/* Eye */}
      <circle cx="50" cy="26" r="3.5" fill="#111111" />
      <circle cx="51" cy="25" r="1" fill="white" opacity="0.6"/>
      {/* Nostril */}
      <ellipse cx="26" cy="55" rx="2.5" ry="2" fill="#111111" transform="rotate(-10 26 55)"/>
    </svg>
  );
}

/** Same logo but inverted (white bg, black horse) for light contexts */
export function HorseLogoLight({ size = 72, className = "" }: HorseLogoProps) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 100 100"
      fill="none" xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect width="100" height="100" rx="22" fill="white" />
      <path
        d="M62,16 C65,10 70,9 72,14 C70,18 66,20 63,22 C67,26 70,32 70,40 C70,50 64,58 56,62 C52,64 48,66 46,70 C44,74 44,80 48,82 C52,84 56,82 58,78 C60,74 60,68 62,64 C68,60 74,52 74,42 C74,32 70,24 64,18 Z"
        fill="#111"
      />
      <path
        d="M36,30 C34,24 36,16 42,14 C48,12 56,14 60,20 C64,26 63,36 58,42 C54,46 48,48 42,46 C36,44 32,38 36,30 Z"
        fill="#111"
      />
      <path
        d="M36,42 C32,44 26,46 24,52 C22,58 26,64 32,64 C36,64 40,62 42,58 C44,54 42,48 38,44 Z"
        fill="#111"
      />
      <path d="M58,14 L62,6 L68,12 L64,16 Z" fill="#111"/>
      <path d="M65,20 C70,12 76,14 76,22 C72,22 68,22 65,20Z" fill="#111"/>
      <path d="M66,28 C72,22 78,26 76,34 C72,32 68,30 66,28Z" fill="#111"/>
      <circle cx="50" cy="26" r="3.5" fill="white"/>
      <ellipse cx="26" cy="55" rx="2.5" ry="2" fill="white" transform="rotate(-10 26 55)"/>
    </svg>
  );
}
