<script lang="ts">
  import QRCode from 'qrcode';
  import { onMount } from 'svelte';

  export let account: string = '';
  export let iban: string = '';
  export let bankName: string = '';
  export let bankCode: string = '';
  export let bic: string = '';
  export let spayd: string = '';
  export let amount: number | null = null;
  export let vs: string = '';

  let qrSvg: string = '';
  let copiedIban = false;
  let copiedAccount = false;

  $: {
    if (spayd) {
      QRCode.toString(spayd, {
        type: 'svg',
        errorCorrectionLevel: 'M',
        margin: 1,
        color: {
          dark: '#0f172a',
          light: '#ffffff'
        }
      }).then((svg) => {
        qrSvg = svg;
      }).catch((err) => {
        console.error('Failed to generate QR Platba:', err);
      });
    }
  }

  function copyText(text: string, type: 'iban' | 'account') {
    navigator.clipboard.writeText(text).then(() => {
      if (type === 'iban') {
        copiedIban = true;
        setTimeout(() => copiedIban = false, 2000);
      } else {
        copiedAccount = true;
        setTimeout(() => copiedAccount = false, 2000);
      }
    });
  }
</script>

<div class="qr-platba-widget">
  <div class="qr-header">
    <div class="qr-brand">
      <span class="qr-icon">💳</span>
      <span class="qr-title">CZECH QR PLATBA</span>
    </div>
    <span class="cba-badge">STANDARD ČBA</span>
  </div>

  <div class="qr-body">
    <div class="qr-code-wrapper">
      {#if qrSvg}
        <div class="qr-svg-container">
          {@html qrSvg}
        </div>
      {:else}
        <div class="qr-placeholder">Generuji QR kód...</div>
      {/if}
      <span class="qr-caption">Naskenujte v mobilním bankovnictví</span>
    </div>

    <div class="qr-details">
      <div class="detail-group">
        <span class="detail-label">Číslo účtu (tuzemské):</span>
        <div class="detail-value-row">
          <code class="detail-code">{account || 'Neuvedeno'}</code>
          {#if account}
            <button
              class="copy-btn"
              on:click={() => copyText(account, 'account')}
              title="Kopírovat číslo účtu"
            >
              {copiedAccount ? 'Zkopírováno!' : 'Kopírovat'}
            </button>
          {/if}
        </div>
      </div>

      <div class="detail-group">
        <span class="detail-label">Mezinárodní formát IBAN:</span>
        <div class="detail-value-row">
          <code class="detail-code iban-code">{iban || 'Neuvedeno'}</code>
          {#if iban}
            <button
              class="copy-btn"
              on:click={() => copyText(iban, 'iban')}
              title="Kopírovat IBAN"
            >
              {copiedIban ? 'Zkopírováno!' : 'Kopírovat'}
            </button>
          {/if}
        </div>
      </div>

      <div class="detail-row-split">
        <div class="detail-subgroup">
          <span class="detail-label">Banka:</span>
          <span class="detail-val-text">{bankName} ({bankCode})</span>
        </div>
        {#if bic}
          <div class="detail-subgroup">
            <span class="detail-label">SWIFT / BIC:</span>
            <code class="detail-subcode">{bic}</code>
          </div>
        {/if}
      </div>

      {#if amount}
        <div class="detail-group highlight-amount">
          <span class="detail-label">Částka k úhradě:</span>
          <span class="amount-val">{amount.toLocaleString('cs-CZ')} Kč</span>
        </div>
      {/if}

      {#if vs}
        <div class="detail-group">
          <span class="detail-label">Variabilní symbol:</span>
          <code class="detail-code">{vs}</code>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .qr-platba-widget {
    background: var(--bg-card, #ffffff);
    border: 1px solid var(--border-subtle, #e2e8f0);
    border-radius: 8px;
    padding: 1rem;
    margin: 0.75rem 0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .qr-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border-subtle, #e2e8f0);
    padding-bottom: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .qr-brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .qr-icon {
    font-size: 1.1rem;
  }

  .qr-title {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--text-heading, #0f172a);
  }

  .cba-badge {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    background: #e0f2fe;
    color: #0369a1;
  }

  .qr-body {
    display: grid;
    grid-template-columns: 140px 1fr;
    gap: 1rem;
    align-items: start;
  }

  @media (max-width: 480px) {
    .qr-body {
      grid-template-columns: 1fr;
    }
  }

  .qr-code-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
  }

  .qr-svg-container {
    width: 130px;
    height: 130px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .qr-svg-container :global(svg) {
    width: 100%;
    height: 100%;
  }

  .qr-placeholder {
    width: 130px;
    height: 130px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    color: #64748b;
    background: #f8fafc;
    border-radius: 6px;
  }

  .qr-caption {
    font-size: 0.65rem;
    color: var(--text-muted, #64748b);
    text-align: center;
    line-height: 1.2;
  }

  .qr-details {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .detail-group {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .detail-label {
    font-size: 0.7rem;
    color: var(--text-muted, #64748b);
    font-weight: 500;
  }

  .detail-value-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .detail-code {
    font-family: var(--font-mono, monospace);
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-heading, #0f172a);
    background: var(--bg-hover, #f1f5f9);
    padding: 0.15rem 0.35rem;
    border-radius: 4px;
  }

  .iban-code {
    font-size: 0.75rem;
    word-break: break-all;
  }

  .copy-btn {
    font-size: 0.7rem;
    padding: 0.2rem 0.45rem;
    border: 1px solid var(--border-subtle, #cbd5e1);
    background: var(--bg-card, #ffffff);
    color: var(--text-base, #334155);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .copy-btn:hover {
    background: var(--bg-hover, #f8fafc);
    border-color: #94a3b8;
  }

  .detail-row-split {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
    font-size: 0.75rem;
  }

  .detail-val-text {
    font-size: 0.75rem;
    color: var(--text-base, #334155);
    font-weight: 500;
  }

  .detail-subcode {
    font-family: var(--font-mono, monospace);
    font-size: 0.75rem;
    color: var(--text-heading, #0f172a);
  }

  .highlight-amount {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    padding: 0.4rem 0.6rem;
    border-radius: 6px;
  }

  .amount-val {
    font-size: 1rem;
    font-weight: 700;
    color: #166534;
  }
</style>
