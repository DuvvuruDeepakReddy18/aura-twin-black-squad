/** Only publishable identity-provider configuration may cross this boundary. */
export function publicAuthConfig(env = process.env) {
  const url = env.AURA_SUPABASE_URL;
  const key = env.AURA_SUPABASE_PUBLISHABLE_KEY;
  let validUrl = false;
  try {
    const parsed = new URL(url);
    validUrl = parsed.protocol === 'https:' && /^[a-z0-9-]+\.supabase\.co$/.test(parsed.hostname)
      && parsed.pathname === '/' && !parsed.username && !parsed.password && !parsed.search && !parsed.hash;
  } catch { /* Unconfigured authentication keeps the research demo accessible. */ }
  const enabled = validUrl && typeof key === 'string' && /^sb_publishable_[A-Za-z0-9_-]{10,}$/.test(key);
  return {
    enabled,
    provider: enabled ? 'supabase' : null,
    supabaseUrl: enabled ? new URL(url).origin : null,
    publishableKey: enabled ? key : null,
    googleEnabled: enabled && env.AURA_GOOGLE_AUTH_ENABLED === 'true',
    emailDeliveryReady: enabled && env.AURA_PUBLIC_AUTH_EMAIL_ENABLED === 'true',
    emailDeliveryMessage: env.AURA_PUBLIC_AUTH_EMAIL_ENABLED === 'true'
      ? 'Email delivery is configured; account confirmation is required.'
      : 'Public sign-up and recovery emails are not enabled on this deployment. Existing accounts can sign in; the research demo needs no account.',
    message: enabled ? 'Authentication is provided by Supabase.' : 'Account sign-in is unavailable until an identity provider is connected. The research demo needs no account.',
    demoRequiresLogin: false,
  };
}
