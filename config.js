(function () {
  const params = new URLSearchParams(window.location.search);
  const base = params.get('webhook_base') || window.location.origin;
  const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base;
  window.GIGI_CONFIG = {
    webhookBase: normalizedBase,
    tonWebhookUrl: `${normalizedBase}/ton-webhook`,
    evmWebhookUrl: `${normalizedBase}/evm-webhook`,
    solanaWebhookUrl: `${normalizedBase}/solana-webhook`,
    tonConnectManifestUrl: `${normalizedBase}/tonconnect-manifest.json`
  };
})();
