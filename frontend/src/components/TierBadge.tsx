interface TierBadgeProps {
  tier: 1 | 2 | 3
  xpath_cached?: boolean
}

const TIER_CLASSES: Record<number, string> = {
  1: 'tier-badge tier-badge--green',
  2: 'tier-badge tier-badge--amber',
  3: 'tier-badge tier-badge--red',
}

export function TierBadge({ tier, xpath_cached }: TierBadgeProps) {
  return (
    <span className={TIER_CLASSES[tier]}>
      {`T${tier}`}
      {xpath_cached && <span className="tier-badge__cached"> cached</span>}
    </span>
  )
}
